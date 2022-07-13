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
"""lsq algorithm"""
from mindspore.nn import Cell
from mindspore._checkparam import Validator
from ..constant import QuantDtype
from ..simulated_quantization.simulated_quantization_aware_training import SimulatedQuantizationAwareTraining as SimQAT
from .learned_step_size_quantization_net_policy import LearnedStepSizeQuantizationNetPolicy as LsqNetPolicy
from .learned_step_size_quantization_config import LearnedStepSizeQuantizationConfig as LsqConfig
from .learned_step_size_fake_quantizers import LearnedStepSizeFakeQuantizerPerLayer as LsqFqPerLayer, \
    LearnedStepSizeFakeQuantizePerChannel as LsqFqPerChannel
from ..quantize_wrapper_cell import QuantizeWrapperCell


class LearnedStepSizeQuantizationAwareTraining(SimQAT):
    """
    Derived class of SimQAT. LSQ quantization algorithm.

    Args:
        config (dict): store attributes for quantization aware training, keys are attribute names,
            values are attribute values. supported attribute are listed below:

            - bn_fold (bool): Whether to use bn fold ops for simulation inference operation.
              Default: False.

    Raises:
        ValueError: `freeze_bn` is less than 0.
        ValueError: If the length of `quant_delay`, `quant_dtype`, `per_channel`, `symmetric` or `narrow_range` is not
            less than 2.
        ValueError: If the element of `quant_delay` is less than 0.
        ValueError: If the first element of `per_channel` is True.
        NotImplementedError: If the element of `quant_dtype` is not `QuantDtype.INT8`.
        TypeError: If the element of `quant_delay` is not int.
        TypeError: If the element of `per_channel`, `symmetric`, `narrow_range`, `bn_fold`, `one_conv_fold` is not bool.
        TypeError: If the element of `quant_dtype` is not `QuantDtype`.
        TypeError: If `freeze_bn` is not int.

    Supported Platforms:
        ``GPU``

    Examples:
        >>> from mindspore_gs.quantization.learned_step_size_quantization \
        >>>     import LearnedStepSizeQuantizationAwareTraining
        >>> from mindspore import nn
        >>> from mindspore.common.initializer import Normal
        ... class NetToQuant(nn.Cell):
        ...     def __init__(self, num_channel=1):
        ...         super(NetToQuant, self).__init__()
        ...         self.conv = nn.Conv2d(num_channel, 6, 5, pad_mode='valid')
        ...         self.bn = nn.BatchNorm2d(6)
        ...
        ...     def construct(self, x):
        ...         x = self.conv(x)
        ...         x = self.bn(x)
        ...         return x
        ...
        ...
        >>> ## 1) Define network to be quantized
        >>> net = NetToQuant()
        >>> ## 2) Define LSQ Algorithm
        >>> learned_quantization = LearnedStepSizeQuantizationAwareTraining()
        >>> ## 3) Use set functions to change config
        >>> learned_quantization.set_enable_fusion(True)
        >>> learned_quantization.set_bn_fold(False)
        >>> learned_quantization.set_act_symmetric(True)
        >>> learned_quantization.set_weight_symmetric(True)
        >>> learned_quantization.set_act_narrow_range(True)
        >>> learned_quantization.set_weight_narrow_range(True)
        >>> learned_quantization.set_act_quant_delay(0)
        >>> learned_quantization.set_weight_quant_delay(0)
        >>> ## 4) Apply LSQ algorithm to origin network
        >>> net_qat = learned_quantization.apply(net)
        >>> ## 5) Print network and check the result. Conv2d and Dense should be transformed to QuantizeWrapperCells.
        >>> ## Since we set enable_fusion to be True, bn_fold to be False, the Conv2d and BatchNorm2d Cells are
        >>> ## fused and converted to Conv2dBnWithoutFoldQuant.
        >>> ## Since we set act_symmetric to be True, the symmetric value of _input_quantizer and _output_quantizer
        >>> ## are set to be True.
        >>> ## Since we set weight_symmetric to be True, the symmetric value of fake_quant_weight are set to be
        >>> ## True.
        >>> ## Since we set act_narrow_range to be True, the narrow_range value of _input_quantizer and
        >>> ## _output_quantizer are set to be True.
        >>> ## Since we set weight_narrow_range to be True, the narrow_range value of fake_quant_weight are set to be
        >>> ## True.
        >>> ## Since we set act_quant_delay to be 0, the quant_delay value of _input_quantizer and _output_quantizer
        >>> ## are set to be 0.
        >>> ## Since we set weight_quant_delay to be 0, the quant_delay value of fake_quant_weight are set to be 0.
        >>> print(net_qat)
        NetToQuantOpt<
          (_handler): NetToQuant<
            (conv): Conv2d<input_channels=1, output_channels=6, kernel_size=(5, 5), stride=(1, 1), pad_mode=valid, padding=0, dilation=(1, 1), group=1, has_bias=False, weight_init=normal, bias_init=zeros, format=NCHW>
            (bn): BatchNorm2d<num_features=6, eps=1e-05, momentum=0.09999999999999998, gamma=Parameter (name=_handler.bn.gamma, shape=(6,), dtype=Float32, requires_grad=True), beta=Parameter (name=_handler.bn.beta, shape=(6,), dtype=Float32, requires_grad=True), moving_mean=Parameter (name=_handler.bn.moving_mean, shape=(6,), dtype=Float32, requires_grad=False), moving_variance=Parameter (name=_handler.bn.moving_variance, shape=(6,), dtype=Float32, requires_grad=False)>
            >
          (Conv2dBnWithoutFoldQuant): QuantizeWrapperCell<
            handler: in_channels=1, out_channels=6, kernel_size=(5, 5), stride=(1, 1), pad_mode=valid, padding=0, dilation=(1, 1), group=1, has_bias=False, input quantizer: bit_num=8, neg_trunc=False, symmetric=True, narrow_range=True, per_channel=False, quant_delay=0, output quantizer: bit_num=8, neg_trunc=False, symmetric=True, narrow_range=True, per_channel=False, quant_delay=0
            (_handler): Conv2dBnWithoutFoldQuant<
              in_channels=1, out_channels=6, kernel_size=(5, 5), stride=(1, 1), pad_mode=valid, padding=0, dilation=(1, 1), group=1, has_bias=False
              (fake_quant_weight): LearnedStepSizeFakeQuantizePerChannel<num_bits=8, symmetric=True, narrow_range=True, neg_trunc=False, per_channel=True(0, 6), quant_delay=0>
              (batchnorm): BatchNorm2d<num_features=6, eps=1e-05, momentum=0.0030000000000000027, gamma=Parameter (name=Conv2dBnWithoutFoldQuant._handler.batchnorm.gamma, shape=(6,), dtype=Float32, requires_grad=True), beta=Parameter (name=Conv2dBnWithoutFoldQuant._handler.batchnorm.beta, shape=(6,), dtype=Float32, requires_grad=True), moving_mean=Parameter (name=Conv2dBnWithoutFoldQuant._handler.batchnorm.moving_mean, shape=(6,), dtype=Float32, requires_grad=False), moving_variance=Parameter (name=Conv2dBnWithoutFoldQuant._handler.batchnorm.moving_variance, shape=(6,), dtype=Float32, requires_grad=False)>
              >
            (_input_quantizer): LearnedStepSizeFakeQuantizerPerLayer<bit_num=8, neg_trunc=False, symmetric=True, narrow_range=True, per_channel=False, quant_delay=0>
            (_output_quantizer): LearnedStepSizeFakeQuantizerPerLayer<bit_num=8, neg_trunc=False, symmetric=True, narrow_range=True, per_channel=False, quant_delay=0>
            >
          >
    """

    def set_act_symmetric(self, act_symmetric):
        """
        Raises:
            TypeError: If `act_symmetric` is not bool.
            NotImplementedError:  Learned scale quantization only support `act_symmetric` is True currently.
        """
        Validator.check_bool(act_symmetric, "act_symmetric", self.__class__.__name__)
        if not act_symmetric:
            raise NotImplementedError("Learned scale quantization only support `act_symmetric` is True currently")
        super(LearnedStepSizeQuantizationAwareTraining, self).set_act_symmetric(act_symmetric)

    def set_weight_symmetric(self, weight_symmetric):
        """
        Raises:
            TypeError: If `weight_symmetric` is not bool.
            NotImplementedError:  Learned scale quantization only support `weight_symmetric` is True currently.
        """
        Validator.check_bool(weight_symmetric, "weight_symmetric", self.__class__.__name__)
        if not weight_symmetric:
            raise NotImplementedError("Learned scale quantization only support `weight_symmetric` is True currently")
        super(LearnedStepSizeQuantizationAwareTraining, self).set_act_symmetric(weight_symmetric)

    def set_act_narrow_range(self, act_narrow_range):
        """
        Raises:
            TypeError: If `act_narrow_range` is not bool.
            NotImplementedError:  Learned scale quantization only support `act_narrow_range` is True currently
        """
        Validator.check_bool(act_narrow_range, "act_narrow_range", self.__class__.__name__)
        if not act_narrow_range:
            raise NotImplementedError("Learned scale quantization only support `act_narrow_range` is True currently")
        self._config.act_narrow_range = act_narrow_range

    def set_weight_narrow_range(self, weight_narrow_range):
        """
        Raises:
            TypeError: If `weight_narrow_range` is not bool.
            NotImplementedError:  Learned scale quantization only support `weight_narrow_range` is True currently
        """
        Validator.check_bool(weight_narrow_range, "weight_narrow_range", self.__class__.__name__)
        if not weight_narrow_range:
            raise NotImplementedError("Learned scale quantization only support `weight_narrow_range` is True "
                                      "currently")
        super(LearnedStepSizeQuantizationAwareTraining, self).set_weight_narrow_range(weight_narrow_range)

    def set_act_quant_delay(self, act_quant_delay):
        """
        Raises:
            TypeError: If `act_quant_delay` is not int.
            NotImplementedError:  Learned scale quantization only support `act_quant_delay` is 0 currently
        """
        Validator.check_is_int(act_quant_delay, "act_quant_delay", self.__class__.__name__)
        if act_quant_delay != 0:
            raise NotImplementedError("Learned scale quantization only support `act_quant_delay` is 0 currently")
        super(LearnedStepSizeQuantizationAwareTraining, self).set_act_quant_delay(act_quant_delay)

    def set_weight_quant_delay(self, weight_quant_delay):
        """
        Raises:
            TypeError: If `weight_quant_delay` is not int.
            NotImplementedError:  Learned scale quantization only support `weight_quant_delay` is 0 currently
        """
        Validator.check_is_int(weight_quant_delay, "weight_quant_delay", self.__class__.__name__)
        if weight_quant_delay != 0:
            raise NotImplementedError("Learned scale quantization only support `weight_quant_delay` is 0 currently")
        super(LearnedStepSizeQuantizationAwareTraining, self).set_weight_quant_delay(weight_quant_delay)

    def set_freeze_bn(self, freeze_bn):
        """
        Raises:
            TypeError: If `freeze_bn` is not int.
            NotImplementedError:  Learned scale quantization only support `freeze_bn` is 0 currently
        """
        Validator.check_is_int(freeze_bn, "freeze_bn", self.__class__.__name__)
        if freeze_bn != 0:
            raise NotImplementedError("Learned scale quantization only support `freeze_bn` is 0 currently")
        super(LearnedStepSizeQuantizationAwareTraining, self).set_freeze_bn(freeze_bn)

    def apply(self, network: Cell) -> Cell:
        """
        Apply LSQ Algorithm on `network`, use the following steps to make `network` available for quantization aware
        training:
        1. Fuse certain cells in `network` using pattern engine which is defined by net policy.
        2. Propagate layer policies defined through cells.
        3. Reduce redundant fake quantizers when they are redundant.
        4. Apply layer policies to convert normal cell to `QuantizeWrapperCell`.

        Args:
            network (Cell): Network to be quantized.

        Returns:
            Quantized network.
        """
        quanted_net = super(LearnedStepSizeQuantizationAwareTraining, self).apply(network)
        self._reset_weights_quantization_params(quanted_net)
        return quanted_net

    def _reset_weights_quantization_params(self, network: Cell):
        for _, cell in network.name_cells().items():
            if isinstance(cell, QuantizeWrapperCell):
                weight_fq = cell.get_handler().fake_quant_weight
                if isinstance(weight_fq, (LsqFqPerLayer, LsqFqPerChannel)):
                    weight_fq.compute_quant_param(cell.get_handler().weight)

    def _init_net_policy(self, config):
        return LsqNetPolicy(config)

    def _create_qconfig_by_dict(self, config: dict):
        self._config = LsqConfig()
        quant_dtype_list = SimQAT._convert2list("quant dtype",
                                                config.get("quant_dtype", [QuantDtype.INT8, QuantDtype.INT8]))
        per_channel_list = SimQAT._convert2list("per channel", config.get("per_channel", [False, True]))
        self.set_act_quant_dtype(quant_dtype_list[0])
        self.set_weight_quant_dtype(quant_dtype_list[-1])

        self.set_act_per_channel(per_channel_list[0])
        self.set_weight_per_channel(per_channel_list[-1])

        self.set_act_symmetric(True)
        self.set_weight_symmetric(True)
        self.set_act_quant_delay(0)
        self.set_weight_quant_delay(0)
        self.set_act_narrow_range(True)
        self.set_weight_narrow_range(True)

        self.set_enable_fusion(config.get("enable_fusion", False))
        self.set_bn_fold(config.get("bn_fold", False))
        self.set_one_conv_fold(config.get("one_conv_fold", True))
        self.set_freeze_bn(0)
