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
"""Conv2dBnWithoutFoldQuant."""
from __future__ import absolute_import

from mindspore.ops import operations as P
from mindspore.common.parameter import Parameter
from mindspore.common.initializer import initializer
from mindspore._checkparam import Validator, twice
from mindspore.nn.layer.normalization import BatchNorm2d
from mindspore.nn.cell import Cell
from ...quantization.simulated_quantization.combined import Conv2dBn
from .fake_quant_with_min_max_observer import quant_config_default, QuantConfig


class Conv2dBnWithoutFoldQuant(Cell):
    r"""
    2D convolution and batchnorm without fold with fake quantized construct.

    This part is a more detailed overview of Conv2d operation. For more details about Quantization,
    please refer to the implementation of class of `FakeQuantWithMinMaxObserver`,
    :class:`mindspore.nn.FakeQuantWithMinMaxObserver`.

    .. math::
        y =x\times quant(w)+  b

        y_{bn} =\frac{y-E[y] }{\sqrt{Var[y]+  \epsilon  } } *\gamma +  \beta

    where :math:`quant` is the continuous execution of quant and dequant, you can refer to the implementation of
    class of `FakeQuantWithMinMaxObserver`, :class:`mindspore.nn.FakeQuantWithMinMaxObserver`.

    Args:
        in_channels (int): The number of input channel :math:`C_{in}`.
        out_channels (int): The number of output channel :math:`C_{out}`.
        kernel_size (Union[int, tuple[int]]): Specifies the height and width of the 2D convolution window.
        stride (Union[int, tuple[int]]): Specifies stride for all spatial dimensions with the same value. Default: 1.
        pad_mode (str): Specifies padding mode. The optional values are "same", "valid", "pad". Default: "same".
        padding (Union[int, tuple[int]]): Implicit paddings on both sides of the `x`. Default: 0.
        dilation (Union[int, tuple[int]]): Specifies the dilation rate to use for dilated convolution. Default: 1.
        group (int): Splits filter into groups, `in_ channels` and `out_channels` must be
            divisible by the number of groups. Default: 1.
        has_bias (bool): Specifies whether the layer uses a bias vector. Default: False.
        eps (float): Parameters for Batch Normalization. Default: 1e-5.
        momentum (float): Parameters for Batch Normalization op. Default: 0.997.
        weight_init (Union[Tensor, str, Initializer, numbers.Number]): Initializer for the convolution kernel.
            Default: 'normal'.
        bias_init (Union[Tensor, str, Initializer, numbers.Number]): Initializer for the bias vector. Default: 'zeros'.
        quant_config (QuantConfig): Configures the types of quant observer and quant settings of weight and
            activation. Note that, QuantConfig is a special namedtuple, which is designed for quantization
            and can be generated by :func:`mindspore.compression.quant.create_quant_config` method.
            Default: QuantConfig with both items set to default :class:`FakeQuantWithMinMaxObserver`.

    Inputs:
        - **x** (Tensor) - Tensor of shape :math:`(N, C_{in}, H_{in}, W_{in})`.

    Outputs:
        Tensor of shape :math:`(N, C_{out}, H_{out}, W_{out})`.

    Supported Platforms:
        ``Ascend`` ``GPU``

    Raises:
        TypeError: If `in_channels`, `out_channels` or `group` is not an int.
        TypeError: If `kernel_size`, `stride`, `padding` or `dilation` is neither an int nor a tuple.
        TypeError: If `has_bias` is not a bool.
        ValueError: If `in_channels`, `out_channels`, `kernel_size`, `stride` or `dilation` is less than 1.
        ValueError: If `padding` is less than 0.
        ValueError: If `pad_mode` is not one of 'same', 'valid', 'pad'.

    Examples:
        >>> import numpy as np
        >>> import mindspore
        >>> from mindspore.compression import quant
        >>> from mindspore import Tensor, nn
        >>> qconfig = quant.create_quant_config()
        >>> conv2d_no_bnfold = nn.Conv2dBnWithoutFoldQuant(1, 1, kernel_size=(2, 2), stride=(1, 1), pad_mode="valid",
        ...                                                weight_init='ones', quant_config=qconfig)
        >>> x = Tensor(np.array([[[[1, 0, 3], [1, 4, 7], [2, 5, 2]]]]), mindspore.float32)
        >>> result = conv2d_no_bnfold(x)
        >>> print(result)
        [[[[5.929658  13.835868]
           [11.859316  17.78116]]]]
    """

    def __init__(self,
                 in_channels,
                 out_channels,
                 kernel_size,
                 stride=1,
                 pad_mode='same',
                 padding=0,
                 dilation=1,
                 group=1,
                 has_bias=False,
                 eps=1e-5,
                 momentum=0.997,
                 weight_init='normal',
                 bias_init='zeros',
                 quant_config=quant_config_default):
        """Initialize Conv2dBnWithoutFoldQuant."""
        super(Conv2dBnWithoutFoldQuant, self).__init__()
        self.in_channels = Validator.check_positive_int(in_channels, "in_channels", self.cls_name)
        self.out_channels = Validator.check_positive_int(out_channels, "out_channels", self.cls_name)
        self.has_bias = has_bias
        self.kernel_size = twice(kernel_size)
        self.stride = twice(stride)
        self.dilation = twice(dilation)
        for kernel_size_elem in self.kernel_size:
            Validator.check_positive_int(kernel_size_elem, 'kernel_size item', self.cls_name)
        for stride_elem in self.stride:
            Validator.check_positive_int(stride_elem, 'stride item', self.cls_name)
        for dilation_elem in self.dilation:
            Validator.check_positive_int(dilation_elem, 'dilation item', self.cls_name)
        if pad_mode not in ('valid', 'same', 'pad'):
            raise ValueError(f"For '{self.cls_name}', the 'pad_mode' must be one of values in "
                             f"('valid', 'same', 'pad'), but got {pad_mode}.")
        self.pad_mode = pad_mode
        if isinstance(padding, int):
            Validator.check_non_negative_int(padding, 'padding', self.cls_name)
            self.padding = padding
        elif isinstance(padding, tuple):
            for pad in padding:
                Validator.check_non_negative_int(pad, 'padding item', self.cls_name)
            self.padding = padding
        else:
            raise TypeError(f"For '{self.cls_name}', the type of 'padding' must be int/tuple(int), "
                            f"but got {type(padding).__name__}!")
        self.group = Validator.check_positive_int(group, "group", self.cls_name)
        self.bias_add = P.BiasAdd()
        if Validator.check_bool(has_bias, "has_bias", self.cls_name):
            self.bias = Parameter(initializer(bias_init, [out_channels]), name='bias')
        else:
            self.bias = None
        # initialize convolution op and Parameter
        self.conv = P.Conv2D(out_channel=self.out_channels,
                             kernel_size=self.kernel_size,
                             mode=1,
                             pad_mode=self.pad_mode,
                             pad=self.padding,
                             stride=self.stride,
                             dilation=self.dilation,
                             group=self.group)
        weight_shape = [out_channels, in_channels // group, *self.kernel_size]
        channel_axis = 0
        self.weight = Parameter(initializer(weight_init, weight_shape), name='weight')
        self.fake_quant_weight = quant_config.weight(channel_axis=channel_axis,
                                                     num_channels=out_channels)
        self.batchnorm = BatchNorm2d(out_channels, eps=eps, momentum=momentum)

    @classmethod
    def from_float(cls, convbn: Conv2dBn, quant_config: QuantConfig):
        """
        A class method to create `Conv2dBnWithoutFoldQuant` from`Conv2dBn`
        """
        conv_quant = cls(in_channels=convbn.conv.in_channels,
                         out_channels=convbn.conv.out_channels,
                         kernel_size=convbn.conv.kernel_size,
                         stride=convbn.conv.stride,
                         pad_mode=convbn.conv.pad_mode,
                         padding=convbn.conv.padding,
                         dilation=convbn.conv.dilation,
                         group=convbn.conv.group,
                         eps=convbn.batchnorm.eps,
                         momentum=convbn.batchnorm.momentum,
                         has_bias=convbn.conv.has_bias,
                         bias_init=convbn.conv.bias_init,
                         weight_init=convbn.conv.weight_init,
                         quant_config=quant_config)
        conv_quant.batchnorm.gamma = convbn.batchnorm.gamma
        conv_quant.batchnorm.beta = convbn.batchnorm.beta
        conv_quant.batchnorm.moving_mean = convbn.batchnorm.moving_mean
        conv_quant.batchnorm.moving_variance = convbn.batchnorm.moving_variance
        conv_quant.weight = convbn.conv.weight
        if convbn.conv.has_bias:
            conv_quant.bias = convbn.conv.bias
        return conv_quant

    def construct(self, x):
        """construct."""
        weight = self.fake_quant_weight(self.weight)
        out = self.conv(x, weight)
        if self.has_bias:
            out = self.bias_add(out, self.bias)
        out = self.batchnorm(out)
        return out

    def extend_repr(self):
        """Display instance object as string."""
        s = 'in_channels={}, out_channels={}, kernel_size={}, stride={}, ' \
            'pad_mode={}, padding={}, dilation={}, group={}, ' \
            'has_bias={}'.format(self.in_channels, self.out_channels, self.kernel_size, self.stride, self.pad_mode,
                                 self.padding, self.dilation, self.group, self.has_bias)
        return s