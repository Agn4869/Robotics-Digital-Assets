# License scope and attribution / 许可与署名

Copyright © 2026 Agn4869. Repository: https://github.com/Agn4869/Robotics-Digital-Assets

## Assets, model descriptions and gallery

Unless a file explicitly states otherwise, `assets/`, `docs/images/`, and the repository documentation are licensed under **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**. See [LICENSE](LICENSE) and https://creativecommons.org/licenses/by-nc/4.0/.

**Attribution is a license condition, not an optional courtesy when sharing the licensed material.** When publicly sharing these assets, including modified versions, retain Agn4869's attribution, the source URL, the license notice and warranty disclaimer, and indicate modifications. Use a reasonable visible credit in your repository README, model card, dataset documentation, video description or figure caption, as appropriate to the medium. Do not imply endorsement. Commercial use of these assets is not granted by this license; contact the maintainer for separate permission.

Suggested attribution (add an actual change statement if modified):

> UVDMS assets from Robotics-Digital-Assets by Agn4869, https://github.com/Agn4869/Robotics-Digital-Assets, licensed under CC BY-NC 4.0. Changes: none.

This notice explains, and does not replace or expand, the standard license. Statutory exceptions remain applicable. The license does not require a citation for every private use or automatically govern every research result that does not share licensed material. If these assets support your research, **please cite the repository in the paper's methods or acknowledgements** using [CITATION.cff](CITATION.cff).

## Code

Python files under `tools/` and `examples/` are MIT-licensed; see [LICENSE-CODE](LICENSE-CODE). Keep their copyright and license notices. The MIT permission for code does not relicense model assets or remove their noncommercial/attribution requirements. Third-party packages are installed separately and retain their own licenses.
## Third-party environment assets

`assets/environments/` contains separately licensed upstream files and derivatives. They are **not** covered by the root CC BY-NC license unless a file explicitly says so:

- AM-Bench mechanism USD assets: Apache-2.0, copyright The AM-Bench Contributors. Retained in `assets/environments/ambench/`.
- WasserMan-derived marine mechanisms and industrial handwheel module: Apache-2.0 upstream terms and notices retained alongside the files. Source: https://github.com/dancher00/wasserman.
- Poly Haven `green_metal_rust` and `modular_industrial_pipes_01` textures/source materials: CC0-1.0, with provenance retained in the environment directory.

See [assets/environments/README.md](assets/environments/README.md), [SOURCES.md](assets/environments/SOURCES.md), individual `NOTICE.md`/`LICENSE.txt` files, and [manifest.json](assets/environments/manifest.json). Do not apply the root noncommercial license to an upstream Apache-2.0 or CC0 file when its own license permits broader use.

## 来源与边界

本仓库由Agn4869发布和维护。本次发布不包含原始SolidWorks工程、博士论文原文/截图或训练数据；环境目录仅包含已导出的、带来源和许可证的交互资产。

模型基于ARMs UVDMS平台及本项目提供的CAD导出；平台背景与部分物理参数参考熊昕飏博士论文《水下航行器-双臂机械手动力学耦合分析及协调控制》，华中科技大学，2025。Agn4869的资产整理/转换署名不替代原平台和学术来源的贡献归属，也不声称论文图片权利。

**公开分享本模型或其修改版时，必须保留Agn4869署名、仓库链接、CC BY-NC 4.0许可及免责声明，并注明修改。** 公开展示中涉及授权素材时，应在图注、视频简介或项目说明中作合理署名。许可不授予资产商用权；工具脚本MIT许可不改变资产的非商用条件。标准CC许可不等于对所有私人使用或不含授权素材的研究结果强制论文引用；科研使用请在方法或致谢中引用本仓库。

Assets and examples are provided as-is, without safety, fitness, hardware calibration or real-robot performance guarantees. Joint effort limits, controller gains and simplified collision shapes are simulation assumptions, not instructions for operating hardware.
