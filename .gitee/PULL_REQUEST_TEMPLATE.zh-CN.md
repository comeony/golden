## 需求（目的，解决什么问题，提供什么能力）

## 描述（具体做了什么，接口有无变更，接口变更的原因）

## 相关的Issue

## 日志白名单
如果新增报错日志或者修改报错日志需要提供报错白名单，其中**用户是否可定位**：表示当前报错是用户的输入有误，用户可以根据报错日志定位到自己的输入有何种错误。

<!--
示例：
| 文件路径 | 报错代码行 | 报错日志类型 | 出错场景和错误分析 | 用户是否可定位 | 定位说明（无法定位的需要给出原因） |
| :-----: | :-----: | :-----: | :-----: | :-----: | :-----: |
| mindspore_gs\quantization\simulated_quantization\simulated_quantization_aware_training.py | 115 | TypeError | 用户输入的config参数不是一个字典 | 是 | 日志中说明了是用户输入的config参数有误，说明了该参数期望的类型 |
| mindspore_gs\quantization\simulated_quantization\simulated_quantization_layer_policy.py | 60 | NotImplementedError | SimQAT算法中配置了perchannel的激活量化，当前算法不支持 | 否 | 该配置项在对外接口处已经做了白名单校验，此处获取到不支持的场景值，应该是内部参数传递有误，不是用户输入有误 |
-->

## 规范
- [ ] 涉及新增对外接口或者修改对外接口
    - [ ] 对外接口变更是否评审并发邮件广播
    - [ ] 对外接口的参数是否在代码中做了校验和白名单过滤
    - [ ] 对外接口是否增加了用例看护
- [ ] 涉及新增算法
    - [ ] 算法应用后的网络结构变更是否如期望，并添加用例看护
    - [ ] 算法是否支持CPU，并添加精度用例看护
    - [ ] 算法是否支持GPU，并添加精度用例看护
    - [ ] 算法是否支持Ascend，并添加精度用例看护
    - [ ] 算法是否支持Graph模式，并添加精度用例看护
    - [ ] 算法是否支持PyNative模式，并添加精度用例看护
    - [ ] 算法的性能是否测试，相比于原始网络，性能是否有严重下降（2倍及以上），如果有，请在**描述**中做说明