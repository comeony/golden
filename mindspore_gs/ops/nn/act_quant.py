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
"""ActQuant."""
from __future__ import absolute_import

from mindspore_gs.validator import Validator
from mindspore.common.dtype import QuantDtype
from mindspore.nn.cell import Cell
from mindspore import nn
from .fake_quant_with_min_max_observer import quant_config_default


class _QuantActivation(Cell):
    r"""
    Base class for quantization aware training activation function. Adds fake quantized operation
    after activation operation.
    """

    def get_origin(self):
        """get_origin."""
        raise NotImplementedError


class ActQuant(_QuantActivation):
    r"""
    Quantization aware training activation function.

    Add the fake quantized operation to the end of activation operation, by which the output of activation
    operation will be truncated. For more details about Quantization, please refer to the implementation
    of subclass of `FakeQuantWithMinMaxObserver`, :class:`mindspore.nn.FakeQuantWithMinMaxObserver`.

    Args:
        activation (Cell): Activation cell.
        ema (bool): The exponential Moving Average algorithm updates min and max. Default: False.
        ema_decay (float): Exponential Moving Average algorithm parameter. Default: 0.999.
        fake_before (bool): Whether add fake quantized operation before activation. Default: False.
        quant_config (QuantConfig): Configures the types of quant observer and quant settings of weight and
            activation. Note that, QuantConfig is a special namedtuple, which is designed for quantization
            and can be generated by :func:`mindspore.compression.quant.create_quant_config` method.
            Default: QuantConfig with both items set to default :class:`FakeQuantWithMinMaxObserver`.
        quant_dtype (QuantDtype): Specifies the FakeQuant datatype. Default: QuantDtype.INT8.

    Inputs:
        - **x** (Tensor) - The input of ActQuant. The input dimension is preferably 2D or 4D.

    Outputs:
        Tensor, with the same type and shape as the `x`.

    Raises:
        TypeError: If `activation` is not an instance of Cell.
        TypeError: If `fake_before` is not a bool.

    Supported Platforms:
        ``Ascend`` ``GPU``

    Examples:
        >>> import numpy as np
        >>> import mindspore
        >>> from mindspore.compression import quant
        >>> from mindspore import Tensor
        >>> qconfig = quant.create_quant_config()
        >>> act_quant = nn.ActQuant(nn.ReLU(), quant_config=qconfig)
        >>> x = Tensor(np.array([[1, 2, -1], [-2, 0, -1]]), mindspore.float32)
        >>> result = act_quant(x)
        >>> print(result)
        [[0.9882355 1.9764705 0.       ]
         [0.        0.        0.       ]]
    """

    def __init__(self,
                 activation,
                 ema=False,
                 ema_decay=0.999,
                 fake_before=False,
                 quant_config=quant_config_default,
                 quant_dtype=QuantDtype.INT8):
        """Initialize ActQuant."""
        super(ActQuant, self).__init__()
        act_class = activation.__class__
        act_list = [nn.ReLU, nn.ReLU6]
        self.act = Validator.check_isinstance("activation", activation, Cell)
        self.fake_before = Validator.check_bool(fake_before, "fake_before", self.cls_name)
        if self.fake_before:
            self.fake_quant_act_before = quant_config.activation(min_init=-6,
                                                                 max_init=6,
                                                                 ema=ema,
                                                                 ema_decay=ema_decay,
                                                                 quant_dtype=quant_dtype)
        self.neg_trunc = False
        self.narrow_range = False
        preset_dict = quant_config.activation.p.keywords
        if 'mode' in preset_dict and preset_dict['mode'] == "LEARNED_SCALE" and act_class in act_list:
            self.neg_trunc = True
        elif 'narrow_range' in preset_dict:
            self.narrow_range = preset_dict['narrow_range']

        self.fake_quant_act = quant_config.activation(min_init=-6,
                                                      max_init=6,
                                                      ema=ema,
                                                      ema_decay=ema_decay,
                                                      quant_dtype=quant_dtype,
                                                      neg_trunc=self.neg_trunc,
                                                      narrow_range=self.narrow_range)

    def construct(self, x):
        """construct."""
        if self.fake_before:
            x = self.fake_quant_act_before(x)
        x = self.act(x)
        x = self.fake_quant_act(x)
        return x

    def get_origin(self):
        """get_origin."""
        return self.act
