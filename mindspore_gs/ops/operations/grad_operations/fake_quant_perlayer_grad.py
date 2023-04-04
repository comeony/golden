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
"""
MindSpore golden stick simulated-quantization ops FakeQuantPerLayerGrad.
"""
from mindspore.ops import DataType
from mindspore_gs.validator import Validator as validator
from mindspore_gs.ops.operations import GSCustom, custom_op_attr_register


class FakeQuantPerLayerGrad(GSCustom):
    """
    FakeQuantPerLayerGrad.
    """
    support_quant_bit = [4, 7, 8]

    @custom_op_attr_register
    def __init__(self,
                 num_bits=8,
                 quant_delay=0,
                 symmetric=False,
                 narrow_range=False):
        """Initialize FakeQuantPerLayerGrad OP"""
        support_device = ["GPU"]
        self._check_support_device_target(support_device)
        if num_bits not in self.support_quant_bit:
            raise ValueError(
                f"For '{self._get_custom_op_name()}' attr \'num_bits\' is not support.")

        validator.check_value_type('symmetric', symmetric, (bool,), self._get_custom_op_name())
        validator.check_value_type('narrow_range', narrow_range, (bool,), self._get_custom_op_name())
        validator.check_positive_int(num_bits, 'num_bits', self._get_custom_op_name())
        validator.check_non_negative_int(quant_delay, 'quant_delay', self._get_custom_op_name())

    def _infer_shape(self, dx, x, x_min, x_max):
        """infer_shape."""
        return x

    def _infer_dtype(self, dx, x, x_min, x_max):
        """infer_dtype."""
        return x

    def _get_op_input_names(self) -> (str,):
        """_get_op_input_names"""
        return "gradient", "x", "min_val", "max_val"

    def _get_op_output_names(self) -> (str,):
        """_get_op_output_names"""
        return ("output",)

    def _get_op_dtype_formats(self) -> [[DataType]]:
        """set_op_dtype_format"""
        return [[DataType.F32_Default, DataType.F32_Default,
                 DataType.F32_Default, DataType.F32_Default, DataType.F32_Default]]
