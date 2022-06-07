# Copyright 2022 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""ScopPruner."""

from comp_algo import CompAlgo
import mindspore.nn as nn
import mindspore.ops as ops
import mindspore
from mindspore import Tensor
import mindspore.common.dtype as mstype
from mindspore.ops import constexpr
from mindspore import Parameter


@constexpr
def generate_int(shape):
    """Generate int."""
    return int(shape // 2)


class KfConv2d(nn.Cell):
    """KF Conv2d."""

    def __init__(self, conv_ori, bn_ori):
        super(KfConv2d, self).__init__()
        self.conv = conv_ori
        self.bn = bn_ori
        self.out_channels = self.conv.out_channels
        self.kfscale = Parameter(ops.Ones()((1, self.out_channels, 1, 1), mindspore.float32), requires_grad=True)
        self.kfscale.data.fill(0.5)
        self.concat_op = ops.Concat(axis=0)

    def construct(self, x):
        """Calculate."""
        x = self.conv(x)
        if self.training:
            num_ori = generate_int(x.shape[0])
            x = self.concat_op((self.kfscale * x[:num_ori] + (1 - self.kfscale) * x[num_ori:], x[num_ori:]))
        x = self.bn(x)
        return x


@constexpr
def generate_tensor(shape, mask_list):
    """Generate tensor."""
    mask = ops.Ones()((shape), mstype.float16).asnumpy()
    for i in mask_list:
        mask[:, i, :, :] = 0.0
    new_mask = Tensor(mask)
    new_mask.set_dtype(mstype.bool_)
    return new_mask


class MaskedConv2dbn(nn.Cell):
    """Mask Conv2d and bn."""

    def __init__(self, kf_conv2d_ori):
        super(MaskedConv2dbn, self).__init__()
        self.conv = kf_conv2d_ori.conv
        self.bn = kf_conv2d_ori.bn
        self.zeros = ops.Zeros()
        self.one = ops.Ones()
        self.out_index = Parameter(kf_conv2d_ori.out_index, requires_grad=False)
        self.cast = ops.Cast()
        self.mask = self.out_index.asnumpy().tolist()

    def construct(self, x):
        """Calculate."""
        x = self.conv(x)
        x = self.bn(x)
        mask = self.zeros((x.shape), mstype.float32).asnumpy()
        mask[:, self.mask, :, :] = 1.0
        mask = Tensor(mask)
        x = x * mask
        return x


class PrunedConv2dbn1(nn.Cell):
    """Prune Conv2d and bn."""

    def __init__(self, masked_module):
        super(PrunedConv2dbn1, self).__init__()

        newconv = nn.Conv2d(in_channels=masked_module.conv.in_channels, out_channels=len(masked_module.out_index),
                            kernel_size=masked_module.conv.kernel_size, stride=masked_module.conv.stride,
                            has_bias=False, padding=masked_module.conv.padding, pad_mode='pad')

        weight_data = masked_module.conv.weight.data.clone()
        weight_data = Parameter(ops.Gather()(weight_data, masked_module.out_index, 0), requires_grad=True,
                                name=masked_module.conv.weight.name)
        newconv.weight = weight_data

        newbn = nn.BatchNorm2d(len(masked_module.out_index))
        newbn.gamma = Parameter(ops.Gather()(masked_module.bn.gamma.data.clone(), masked_module.out_index, 0),
                                requires_grad=True, name=masked_module.bn.gamma.name)
        newbn.beta = Parameter(ops.Gather()(masked_module.bn.beta.data.clone(), masked_module.out_index, 0),
                               requires_grad=True, name=masked_module.bn.beta.name)
        newbn.moving_mean = Parameter(
            ops.Gather()(masked_module.bn.moving_mean.data.clone(), masked_module.out_index, 0), requires_grad=False)
        newbn.moving_variance = Parameter(
            ops.Gather()(masked_module.bn.moving_variance.data.clone(), masked_module.out_index, 0),
            requires_grad=False)

        self.conv = newconv
        self.bn = newbn

        self.oriout_channels = masked_module.conv.out_channels
        self.out_index = masked_module.out_index

    def construct(self, x):
        """Calculate."""
        x = self.conv(x)
        x = self.bn(x)
        return x


class PrunedConv2dbnmiddle(nn.Cell):
    """Prune Conv2d and bn."""

    def __init__(self, masked_module):
        super(PrunedConv2dbnmiddle, self).__init__()

        newconv = nn.Conv2d(in_channels=len(masked_module.in_index), out_channels=len(masked_module.out_index),
                            kernel_size=masked_module.conv.kernel_size, stride=masked_module.conv.stride,
                            has_bias=False, padding=masked_module.conv.padding, pad_mode=masked_module.conv.pad_mode)

        weight_data = masked_module.conv.weight.data.clone()
        weight_data = ops.Gather()(ops.Gather()(weight_data, masked_module.out_index, 0), masked_module.in_index, 1)
        newconv.weight = Parameter(weight_data, requires_grad=True, name=masked_module.conv.weight.name)

        newbn = nn.BatchNorm2d(len(masked_module.out_index))
        newbn.gamma = Parameter(ops.Gather()(masked_module.bn.gamma.data.clone(), masked_module.out_index, 0),
                                requires_grad=True, name=masked_module.bn.gamma.name)
        newbn.beta = Parameter(ops.Gather()(masked_module.bn.beta.data.clone(), masked_module.out_index, 0),
                               requires_grad=True, name=masked_module.bn.beta.name)
        newbn.moving_mean = Parameter(
            ops.Gather()(masked_module.bn.moving_mean.data.clone(), masked_module.out_index, 0), requires_grad=False)
        newbn.moving_variance = Parameter(
            ops.Gather()(masked_module.bn.moving_variance.data.clone(), masked_module.out_index, 0),
            requires_grad=False)

        self.conv = newconv
        self.bn = newbn

        self.oriout_channels = masked_module.conv.out_channels
        self.out_index = masked_module.out_index

    def construct(self, x):
        """Calculate."""
        x = self.conv(x)
        x = self.bn(x)
        return x


class PrunedConv2dbn2(nn.Cell):
    """Prune Conv2d and bn."""

    def __init__(self, masked_module):
        super(PrunedConv2dbn2, self).__init__()

        newconv = nn.Conv2d(in_channels=len(masked_module.in_index), out_channels=len(masked_module.out_index),
                            kernel_size=masked_module.conv.kernel_size, stride=masked_module.conv.stride,
                            has_bias=False, padding=masked_module.conv.padding, pad_mode='pad')

        weight_data = masked_module.conv.weight.data.clone()
        weight_data = ops.Gather()(ops.Gather()(weight_data, masked_module.out_index, 0), masked_module.in_index, 1)
        newconv.weight = Parameter(weight_data, requires_grad=True, name=masked_module.conv.weight.name)

        newbn = nn.BatchNorm2d(len(masked_module.out_index))
        newbn.gamma = Parameter(ops.Gather()(masked_module.bn.gamma.data.clone(), masked_module.out_index, 0),
                                requires_grad=True, name=masked_module.bn.gamma.name)
        newbn.beta = Parameter(ops.Gather()(masked_module.bn.beta.data.clone(), masked_module.out_index, 0),
                               requires_grad=True, name=masked_module.bn.beta.name)
        newbn.moving_mean = Parameter(
            ops.Gather()(masked_module.bn.moving_mean.data.clone(), masked_module.out_index, 0), requires_grad=False)
        newbn.moving_variance = Parameter(
            ops.Gather()(masked_module.bn.moving_variance.data.clone(), masked_module.out_index, 0),
            requires_grad=False)

        self.conv = newconv
        self.bn = newbn

        self.oriout_channels = masked_module.conv.out_channels
        self.out_index = masked_module.out_index
        self.zeros = ops.Zeros()

    def construct(self, x):
        """Calculate."""
        x = self.conv(x)
        x = self.bn(x)
        output = self.zeros((x.shape[0], self.oriout_channels, x.shape[2], x.shape[3]))
        output[:, self.out_index, :, :] = x
        return output


class PrunerKfCompressAlgo(CompAlgo):
    """Prune algo."""

    def callbacks(self):
        return self._callback

    def tranform_conv(self, net):
        """Transform conv."""

        def _inject(modules):
            keys = list(modules.keys())
            for ik, k in enumerate(keys):
                if isinstance(modules[k], nn.Conv2d):
                    if k not in ('0', 'conv1_3x3', 'conv1_7x7'):
                        modules[k] = KfConv2d(modules[k], modules[keys[ik + 1]])
                        modules[keys[ik + 1]] = nn.SequentialCell()
                elif (not isinstance(modules[k], KfConv2d)) and modules[k]._cells:
                    _inject(modules[k]._cells)

        _inject(net._cells)
        return net

    def apply(self, network):
        return self.tranform_conv(network)


class PrunerFtCompressAlgo(CompAlgo):
    """Prune algo."""

    def callbacks(self):
        return self._callback

    def recover_conv(self, net):
        """Recover conv."""

        def _inject(modules):
            keys = list(modules.keys())

            for _, k in enumerate(keys):
                if isinstance(modules[k], KfConv2d):
                    modules[k] = MaskedConv2dbn(modules[k])
                elif (not isinstance(modules[k], KfConv2d)) and modules[k]._cells:
                    _inject(modules[k]._cells)

        _inject(net._cells)
        return net

    def pruning_conv(self, net):
        """Prune conv."""

        def _inject(modules):
            keys = list(modules.keys())

            for _, k in enumerate(keys):
                if isinstance(modules[k], MaskedConv2dbn):
                    if 'conv1' in k:
                        modules[k] = PrunedConv2dbn1(modules[k])
                    elif 'conv2' in k:
                        modules[k] = PrunedConv2dbnmiddle(modules[k])
                    elif 'conv3' in k:
                        modules[k] = PrunedConv2dbn2(modules[k])
                elif (not isinstance(modules[k], KfConv2d)) and modules[k]._cells:
                    _inject(modules[k]._cells)

        _inject(net._cells)
        return net

    def apply(self, network):
        return self.recover_conv(network)
