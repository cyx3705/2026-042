# ActionDecoder

在 CAD/EDA 软件里，用户拾取一个实体后，光标旁立刻给出最可能的下一步指令（Top-3），
按一个键采纳；不理会就静默消失。把“在菜单里回忆指令”变成“在光标旁认出指令”。

本地大模型只给固定指令表打分，宿主软件的确定性规则先剔除不合法指令，最后由人选择。
设计取舍见 [`b-Office/现行约定.md`](./b-Office/现行约定.md)。

## 入口

| 入口 | 用途 |
| --- | --- |
| [`AGENTS.md`](./AGENTS.md) | AI 读取顺序、真值规则、工作边界与完成要求 |
| [`project.manifest.json`](./project.manifest.json) | 项目身份、路径、命令和上下文排除项 |
| [`b-Office/现行约定.md`](./b-Office/现行约定.md) | 唯一的长期文档：目标、取舍与未定事项 |

## 合同验证

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\b-Code\Test-ProjectContract.ps1 -Instantiation
```

作者：Pinavia

## 保留内容

### logo与作者

- 作者：pinavia
- ![logo](./Logo.png)

### 学习许可与权利保留

- 本项目允许个人、学校和研究者进行非商业性的学习、研究和引用。
- 未经著作权人书面许可，不得将项目内容用于商业开发、产品制造、商业服务、商业宣传、投标交付、毕业设计成品交付或再授权。
- 不得删除作者、来源、版本历史和第三方许可证声明，不得将本项目或其衍生成果宣称为与作者无关的原创项目。
- 软件源码适用 [PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/)；机械模型、PCB、原理图、图片、文档、Unity 工程和其他非软件资料适用 [CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/)。
- SE、SW、STEP/STP 及其他三维模型仅允许个人或学校进行非商业学习、评审和研究；未经著作权人书面许可，不得用于加工、打样、制造、销售、量产、投标、产品交付、商业宣传、改作或再授权。
- 第三方组件、模板、元件库、外购件模型和工具仍受其原始许可证约束；本声明不扩大作者对第三方内容的权利。

商业使用、产品化、公司内部长期使用、转让或排他性授权需另行取得著作权人的书面许可。
