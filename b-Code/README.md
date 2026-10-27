# ActionDecoder 项目工具

本目录保存项目合同检查等可重复执行的维护工具，不承载业务源码；业务组件按实际建立
`b-Code-<组件名>/` 并登记到 manifest。

`Test-ProjectContract.ps1` 验证 manifest、活动路径、a/b/z 根目录规则、现行文档、本地 Markdown
链接和实例化占位符。脚本只读检查仓库，不提交、推送、发布或修改外部系统。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\b-Code\Test-ProjectContract.ps1 -Instantiation
```
