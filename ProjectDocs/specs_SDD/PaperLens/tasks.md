# PaperLens - 任务分解文档

## 文档信息

| 项目 | 内容 |
|------|------|
| 项目名称 | PaperLens |
| 文档版本 | v1.0 |
| 创建日期 | 2026-07-13 |
| 最后更新 | 2026-07-14 |
| 文档状态 | 已完成 |

## 文档引用说明

本任务文档中的每个任务都包含对需求文档和设计文档的明确引用，确保开发过程的可追溯性。

**引用格式:**
- **需求引用**: spec.md 中的需求 ID（如 FR-01.1.1）
- **设计引用**: design/ 目录下的设计文档路径和章节
- **API 引用**: 具体的 API 接口路径
- **数据模型引用**: 具体的数据表名称
- **前端页面引用**: 前端设计文档中的页面章节

## API 实现状态总览

| 状态 | 接口 |
|------|------|
| ✅ CURRENT | GET /api/v1/health |
| ✅ CURRENT | POST /api/v1/papers/upload（仅 file 字段，title=文件名stem，status=PROCESSING） |
| ✅ CURRENT | GET /api/v1/papers |
| ✅ CURRENT | GET /api/v1/papers/{paper_id} |
| ✅ CURRENT | GET /api/v1/papers/{paper_id}/pages/{page_number} |
| ✅ CURRENT | GET /api/v1/papers/{paper_id}/sections |
| ✅ CURRENT | GET /api/v1/papers/{paper_id}/evidences（无 page_number/evidence_type 过滤） |
| ✅ CURRENT | GET /api/v1/evidences/{evidence_id} |
| ✅ CURRENT | POST /api/v1/papers/{paper_id}/tasks（REVIEW / METRIC_EXTRACTION） |
| ✅ CURRENT | GET /api/v1/papers/{paper_id}/tasks |
| ✅ CURRENT | GET /api/v1/tasks/{task_id} |
| ✅ CURRENT | GET /api/v1/papers/{paper_id}/reviews（仅 VERIFIED Finding） |
| ✅ CURRENT | 10 个 `/api/v1/auth` 端点、真实用户依赖与 USER/ADMIN RBAC 基础（P3.5） |
| 📋 PLANNED | DELETE /api/v1/papers/{paper_id} |
| 📋 PLANNED | GET /api/v1/papers/{paper_id}/tables |
| 📋 PLANNED | POST /api/v1/tasks/{task_id}/cancel |
| ✅ CURRENT | GET /api/v1/papers/{paper_id}/metrics、GET /api/v1/metrics/{metric_id} |
| ✅ CURRENT | POST upload、GET list、GET `/api/v1/experiment-files/{file_id}` 结构详情（P5.1） |
| 📋 PLANNED | ExperimentResult/result API、DELETE 和实验前端（P5.2+） |
| 📋 PLANNED | POST/GET /api/v1/papers/{paper_id}/exports, GET download |
| 📋 PLANNED | POST /api/v1/papers/{paper_id}/index（FAISS） |

**关键实现细节:**
- SHA-256 哈希已计算并存储，去重/复用逻辑 📋 PLANNED
- 认证: 统一 Bearer JWT + AuthSession/User 数据库校验（✅ P3.5 CURRENT）
- Swagger: `/api/docs`，OpenAPI: `/api/openapi.json`

---

## 1. 论文上传与解析

### 1.1 论文上传

**需求引用:**
- FR-01.1.1: 支持单文件 PDF 上传（multipart/form-data）
- FR-01.1.2: 文件类型校验（仅接受包含可提取文本的 PDF）
- FR-01.1.3: 文件大小限制 50MB
- FR-01.1.4: 路径穿越防护
- FR-01.1.5: SHA-256 文件哈希计算与存储（去重/复用逻辑 📋 PLANNED）
- FR-01.1.6: 上传后自动触发后台解析任务

**设计引用:**
- [design/01-论文上传与解析.md#21-论文上传服务](design/01-论文上传与解析.md#21-论文上传服务)
- [design/09-API接口详细设计.md#2-论文管理-api](design/09-API接口详细设计.md#2-论文管理-api)

**前端页面引用:**
- P02 论文上传 (10-前端详细设计.md#4.2-P02-论文上传)

**API 引用:**
- POST /api/v1/papers/upload

**数据模型引用:**
- papers

**验收标准:**
- PDF 文件可成功上传
- 非 PDF 文件返回 415 错误
- 超过 50MB 返回 413 错误
- 上传后状态为 PROCESSING，并注册后台解析任务

#### 任务 1.1.1: PDF 文件上传接口 ✅ DONE

**任务描述**: 实现 POST /api/v1/papers/upload 接口，支持 multipart/form-data 上传 PDF 文件，包含文件类型校验、大小限制、路径穿越防护、SHA-256 哈希存储。

**需求引用:**
- FR-01.1.1: 支持单文件 PDF 上传
- FR-01.1.2: 文件类型校验
- FR-01.1.3: 文件大小限制 50MB
- FR-01.1.4: 路径穿越防护
- FR-01.1.5: SHA-256 哈希计算与存储（去重/复用逻辑 📋 PLANNED）

**设计引用:**
- [design/01-论文上传与解析.md#21-论文上传服务](design/01-论文上传与解析.md#21-论文上传服务)

**API 引用:**
- ✅ CURRENT: POST /api/v1/papers/upload（仅 file 字段，title=文件名stem，status=PROCESSING）

**数据模型引用:**
- papers

**实现要点:**
- multipart/form-data 接收文件
- 检查扩展名 + PDF magic bytes
- 文件大小限制 50MB
- sanitize_filename() 清洗文件名
- SHA-256 哈希计算和存储（去重逻辑 📋 PLANNED）
- StorageBackend.save() 存储文件
- 上传失败时回滚存储和临时文件

**验收标准:**
- 有效 PDF 上传返回 201
- 非 PDF 返回 415
- 超过 50MB 返回 413
- 路径穿越文件名被清洗为 basename

#### 任务 1.1.2: 论文列表与详情接口 ✅ DONE（部分）

**任务描述**: 实现论文列表查询（分页、状态过滤）和论文详情查询接口。

**需求引用:**
- FR-01.1.1: 支持单文件 PDF 上传

**设计引用:**
- [design/01-论文上传与解析.md#21-论文上传服务](design/01-论文上传与解析.md#21-论文上传服务)

**API 引用:**
- ✅ CURRENT: GET /api/v1/papers
- ✅ CURRENT: GET /api/v1/papers/{paper_id}
- 📋 PLANNED: DELETE /api/v1/papers/{paper_id}

**数据模型引用:**
- papers

**实现要点:**
- 分页查询: ?page=1&page_size=20
- 状态过滤: ?status=PARSED
- 📋 PLANNED: 级联删除: 删除论文及所有关联数据
- UUID 路径参数校验

**验收标准:**
- 论文列表可分页查询
- 论文详情含 error_message 字段
- 📋 PLANNED: 删除论文级联删除关联数据

#### 任务 1.1.3: 论文上传前端页面 ✅ DONE

**任务描述**: 实现论文上传页面（P02），支持拖拽/选择 PDF 上传，文件校验，进度显示。

**需求引用:**
- FR-01.1.1: 支持单文件 PDF 上传
- FR-01.1.2: 文件类型校验
- FR-01.1.3: 文件大小限制 50MB

**设计引用:**
- [design/07-前端展示.md#32-p02-论文上传-uploadview--已实现](design/07-前端展示.md#32-p02-论文上传-uploadview--已实现)
- [design/10-前端详细设计.md#42-p02-论文上传-uploadview](design/10-前端详细设计.md#42-p02-论文上传-uploadview)

**前端页面引用:**
- P02 论文上传 (10-前端详细设计.md#4.2-P02-论文上传)

**API 引用:**
- POST /api/v1/papers/upload

**实现要点:**
- 拖拽区: 虚线边框，支持 drag-drop 和点击选择
- 文件校验: 类型（.pdf）和大小（<=50MB）
- 上传进度条
- 上传成功跳转到论文详情

**验收标准:**
- 拖拽和点击选择均可上传
- 非 PDF / 超过 50MB 显示错误
- 上传成功跳转到 /papers/:id

#### 任务 1.1.4: 论文列表前端页面 ✅ DONE

**任务描述**: 实现论文列表页面（P03），表格展示论文列表，状态标签，PROCESSING 轮询。

**需求引用:**
- FR-01.1.1: 支持单文件 PDF 上传

**设计引用:**
- [design/07-前端展示.md#33-p03-论文列表-paperlistview--已实现](design/07-前端展示.md#33-p03-论文列表-paperlistview--已实现)
- [design/10-前端详细设计.md#43-p03-论文列表-paperlistview](design/10-前端详细设计.md#43-p03-论文列表-paperlistview)

**前端页面引用:**
- P03 论文列表 (10-前端详细设计.md#4.3-P03-论文列表)

**API 引用:**
- GET /api/v1/papers

**实现要点:**
- 表格列: 标题、文件名、状态、页数、创建时间、操作
- 状态标签颜色: 解析中(橙) / 已解析(绿) / 失败(红) / 上传中(灰)
- PROCESSING 状态 3 秒轮询
- 组件卸载清除定时器

**验收标准:**
- 论文列表可分页展示
- PROCESSING 状态自动轮询
- 点击"查看"跳转到论文详情

### 1.2 PDF 解析

**需求引用:**
- FR-01.2.1: 使用 PyMuPDF + pdfplumber 提取页面文本
- FR-01.2.2: 生成 normalized_text_content
- FR-01.2.3: 识别章节结构
- FR-01.2.4: 提取页面尺寸
- FR-01.2.5: 仅支持包含可提取文本的 PDF

**设计引用:**
- [design/01-论文上传与解析.md#22-pdf-解析服务](design/01-论文上传与解析.md#22-pdf-解析服务)

**数据模型引用:**
- papers, paper_pages, paper_sections

**验收标准:**
- 上传 PDF 后状态变为 PARSED
- 页面文本和章节结构可查询
- 解析失败状态变为 FAILED

#### 任务 1.2.1: PDF 页面文本提取 ✅ DONE

**任务描述**: 使用 PyMuPDF 提取页面文本和尺寸，生成 normalized_text_content。

**需求引用:**
- FR-01.2.1: 使用 PyMuPDF 提取页面文本
- FR-01.2.2: 生成 normalized_text_content
- FR-01.2.4: 提取页面尺寸
- FR-01.2.5: 仅支持包含可提取文本的 PDF

**设计引用:**
- [design/01-论文上传与解析.md#22-pdf-解析服务](design/01-论文上传与解析.md#22-pdf-解析服务)

**数据模型引用:**
- paper_pages

**实现要点:**
- PyMuPDF 提取页面文本和尺寸
- normalized_text_content: 合并连续空白字符
- 扫描型 PDF 抛出 OCR_NOT_SUPPORTED
- 解析失败设置 error_message

**验收标准:**
- 页面文本和尺寸可提取
- normalized_text_content 空白字符合并
- 扫描型 PDF 抛出异常

#### 任务 1.2.2: 章节结构识别 ✅ DONE

**任务描述**: 识别论文章节结构（ABSTRACT / INTRODUCTION / METHOD 等）。

**需求引用:**
- FR-01.2.3: 识别章节结构

**设计引用:**
- [design/01-论文上传与解析.md#22-pdf-解析服务](design/01-论文上传与解析.md#22-pdf-解析服务)

**数据模型引用:**
- paper_sections

**实现要点:**
- 正则匹配标题模式
- 识别 section_type 枚举
- 记录标题、层级、序号、页码范围

**验收标准:**
- 章节结构可识别和查询
- section_type 正确分类

### 1.3 表格提取

**需求引用:**
- FR-01.3.1: 使用 pdfplumber 提取表格
- FR-01.3.2: 存储为 structured_data 和 raw_text
- FR-01.3.3: 记录表格 bbox 坐标和 caption
- FR-01.3.4: 非法表格使用 SAVEPOINT 降级跳过

**设计引用:**
- [design/01-论文上传与解析.md#22-pdf-解析服务](design/01-论文上传与解析.md#22-pdf-解析服务)

**API 引用:**
- 📋 PLANNED: GET /api/v1/papers/{paper_id}/tables

**数据模型引用:**
- paper_tables

**验收标准:**
- 表格可提取并结构化存储
- 非法表格不影响论文整体解析状态

#### 任务 1.3.1: PDF 表格提取与存储 ✅ DONE（后端存储，API 📋 PLANNED）

**任务描述**: 使用 pdfplumber 提取表格，存储为 structured_data 和 raw_text，处理非法表格降级。

**需求引用:**
- FR-01.3.1: 使用 pdfplumber 提取表格
- FR-01.3.2: 存储为 structured_data 和 raw_text
- FR-01.3.3: 记录表格 bbox 坐标和 caption
- FR-01.3.4: 非法表格使用 SAVEPOINT 降级跳过

**设计引用:**
- [design/01-论文上传与解析.md#22-pdf-解析服务](design/01-论文上传与解析.md#22-pdf-解析服务)

**数据模型引用:**
- paper_tables

**实现要点:**
- pdfplumber 提取表格
- structured_data: JSONB 行列形式
- raw_text: 兜底文本
- SAVEPOINT 降级: page_number=0 的表格跳过

**验收标准:**
- 表格可提取并结构化存储
- 非法表格不影响论文整体解析

### 1.4 文本分块

**需求引用:**
- FR-01.4.1: 按章节/段落分块
- FR-01.4.2: 记录块序号、字符数、涉及页码
- FR-01.4.3: 预留 embedding_id 字段

**设计引用:**
- [design/01-论文上传与解析.md#22-pdf-解析服务](design/01-论文上传与解析.md#22-pdf-解析服务)

**数据模型引用:**
- paper_chunks

**验收标准:**
- 文本分块可查询
- 每个块关联所属章节

#### 任务 1.4.1: 文本分块实现 ✅ DONE

**任务描述**: 按章节/段落对论文文本进行分块，生成 PaperChunk 记录。

**需求引用:**
- FR-01.4.1: 按章节/段落分块
- FR-01.4.2: 记录块序号、字符数、涉及页码
- FR-01.4.3: 预留 embedding_id 字段

**设计引用:**
- [design/01-论文上传与解析.md#22-pdf-解析服务](design/01-论文上传与解析.md#22-pdf-解析服务)

**数据模型引用:**
- paper_chunks

**实现要点:**
- 按章节/段落分块
- 记录 chunk_index、char_count、page_numbers
- 预留 embedding_id 字段
- 分块结果确定性

**验收标准:**
- 文本分块可查询
- 每个块关联所属章节
- 分块结果确定性

---

## 2. 证据提取与检索

### 2.1 Evidence 提取

**需求引用:**
- FR-02.2.1: Evidence 为 page-local 定位
- FR-02.2.2: 使用真实 bbox 坐标和字符偏移
- FR-02.2.3: 支持 TEXT / TABLE / FIGURE_CAPTION / EQUATION 类型

**设计引用:**
- [design/02-证据提取与检索.md#21-evidence-提取服务已实现](design/02-证据提取与检索.md#21-evidence-提取服务已实现)

**API 引用:**
- ✅ CURRENT: GET /api/v1/papers/{paper_id}/evidences（无 page_number/evidence_type 过滤）
- ✅ CURRENT: GET /api/v1/evidences/{evidence_id}

**数据模型引用:**
- evidences

**验收标准:**
- Evidence 可提取并查询（page-local, real bbox）
- 前端可高亮跳转到 Evidence 位置

#### 任务 2.1.1: Evidence 提取与存储 ✅ DONE

**任务描述**: 基于 PyMuPDF block 提取页内 Evidence，计算真实 bbox 坐标和 char 偏移。

**需求引用:**
- FR-02.2.1: Evidence 为 page-local 定位
- FR-02.2.2: 使用真实 bbox 坐标和字符偏移
- FR-02.2.3: 支持 TEXT / TABLE / FIGURE_CAPTION / EQUATION 类型

**设计引用:**
- [design/02-证据提取与检索.md#21-evidence-提取服务已实现](design/02-证据提取与检索.md#21-evidence-提取服务已实现)

**数据模型引用:**
- evidences

**实现要点:**
- PyMuPDF block 提取页内文本块
- 真实 bbox 坐标
- char_start / char_end 在 normalized_text_content 中计算
- char 区间不匹配时设为 null（降级）
- evidence_type 标注

**验收标准:**
- Evidence 可提取并查询
- page-local 定位，不跨页
- char 区间不匹配时降级

#### 任务 2.1.2: Evidence 查询接口 ✅ DONE（无过滤参数）

**任务描述**: 实现 Evidence 列表查询和详情查询接口。

**需求引用:**
- FR-02.2.1: Evidence 为 page-local 定位

**设计引用:**
- [design/02-证据提取与检索.md#21-evidence-提取服务已实现](design/02-证据提取与检索.md#21-evidence-提取服务已实现)
- [design/09-API接口详细设计.md#6-证据-api](design/09-API接口详细设计.md#6-证据-api)

**API 引用:**
- ✅ CURRENT: GET /api/v1/papers/{paper_id}/evidences（无 page_number/evidence_type 过滤）
- ✅ CURRENT: GET /api/v1/evidences/{evidence_id}

**数据模型引用:**
- evidences

**实现要点:**
- 📋 PLANNED: 支持 page_number / evidence_type 过滤
- 详情含页面内定位信息
- nullable 字段返回 null

**验收标准:**
- 📋 PLANNED: Evidence 列表可按页码和类型过滤
- 详情含完整定位信息

### 2.2 论文详情前端页面

**需求引用:**
- FR-02.2.4: 前端基于 normalized_text_content 字符区间高亮

**设计引用:**
- [design/07-前端展示.md#34-p04-论文详情-paperdetailview--已实现](design/07-前端展示.md#34-p04-论文详情-paperdetailview--已实现)
- [design/10-前端详细设计.md#44-p04-论文详情-paperdetailview](design/10-前端详细设计.md#44-p04-论文详情-paperdetailview)

**前端页面引用:**
- P04 论文详情 (10-前端详细设计.md#4.4-P04-论文详情)

**API 引用:**
- GET /api/v1/papers/{paper_id}
- GET /api/v1/papers/{paper_id}/sections
- GET /api/v1/papers/{paper_id}/pages/{page_number}
- GET /api/v1/papers/{paper_id}/evidences

**验收标准:**
- 三 Tab 切换正常
- Evidence 高亮跳转正常
- 降级提示正常

#### 任务 2.2.1: 论文详情页面实现 ✅ DONE

**任务描述**: 实现论文详情页面（P04），含章节/页面/证据三 Tab，Evidence 高亮跳转。

**需求引用:**
- FR-02.2.4: 前端基于 normalized_text_content 字符区间高亮

**设计引用:**
- [design/07-前端展示.md#34-p04-论文详情-paperdetailview--已实现](design/07-前端展示.md#34-p04-论文详情-paperdetailview--已实现)
- [design/10-前端详细设计.md#44-p04-论文详情-paperdetailview](design/10-前端详细设计.md#44-p04-论文详情-paperdetailview)

**API 引用:**
- GET /api/v1/papers/{paper_id}
- GET /api/v1/papers/{paper_id}/sections
- GET /api/v1/papers/{paper_id}/pages/{page_number}
- GET /api/v1/papers/{paper_id}/evidences

**实现要点:**
- 三 Tab 切换: 章节 / 页面 / 证据
- Evidence 高亮: 基于 char_start / char_end
- 降级处理: char 区间无效时显示提示
- PROCESSING 状态 3 秒轮询
- 请求去重: request id 防止陈旧响应覆盖

**验收标准:**
- 章节/页面/证据 Tab 正常切换
- Evidence 高亮跳转正常
- 降级提示正常
- 轮询和去重正常

### 2.3 向量索引（规划）

**需求引用:**
- FR-02.1.1: 调用 Embedding 模型向量化 PaperChunk
- FR-02.1.2: 使用 FAISS 建立向量索引
- FR-02.1.3: 索引可序列化持久化

**设计引用:**
- [design/02-证据提取与检索.md#22-向量索引服务未实现](design/02-证据提取与检索.md#22-向量索引服务未实现)

**数据模型引用:**
- paper_chunks (embedding_id)

**验收标准:**
- 文本块可向量化并索引
- 索引可序列化持久化

#### 任务 2.3.1: FAISS 向量索引构建（规划）

**任务描述**: 实现 PaperChunk 向量化和 FAISS 索引构建。

**需求引用:**
- FR-02.1.1: 调用 Embedding 模型向量化 PaperChunk
- FR-02.1.2: 使用 FAISS 建立向量索引
- FR-02.1.3: 索引可序列化持久化

**设计引用:**
- [design/02-证据提取与检索.md#22-向量索引服务未实现](design/02-证据提取与检索.md#22-向量索引服务未实现)

**数据模型引用:**
- paper_chunks (embedding_id)

**实现要点:**
- Embedding 模型调用
- FAISS IndexFlatIP 构建
- 索引序列化到 OBS
- 回填 PaperChunk.embedding_id

**验收标准:**
- 文本块可向量化并索引
- 索引可序列化持久化

---

## 3. 审阅生成（P3.3 后端已实现）

### 3.1 结构化论文审阅

**需求引用:**
- FR-03.1.1: 按维度生成审阅结果
- FR-03.1.2: 每条 ReviewFinding 必须关联至少一个 Evidence
- FR-03.1.3: 未关联 Evidence 的 Finding 标记为 UNVERIFIED
- FR-03.1.4: 支持 STRENGTH / WEAKNESS / SUGGESTION 类型
- FR-03.1.5: 评分 1-5，含 overall_verdict

**设计引用:**
- [design/03-审阅生成.md#21-审阅生成服务](design/03-审阅生成.md#21-审阅生成服务)

**API 引用:**
- POST /api/v1/papers/{paper_id}/tasks (task_type=REVIEW)
- GET /api/v1/papers/{paper_id}/tasks
- GET /api/v1/tasks/{task_id}
- GET /api/v1/papers/{paper_id}/reviews

**数据模型引用:**
- analysis_tasks, review_results, review_findings, finding_evidences

**验收标准:**
- 审阅结果 API 返回含 Evidence 的结构化结果
- UNVERIFIED Finding 不展示

#### 任务 3.1.1: 审阅生成后端服务 ✅ DONE（P3.1 MockLLM，P3.2 语义检索，P3.3 Huawei MaaS LLM）

**任务描述**: 实现审阅生成服务，基于 Evidence 和 LLM 生成结构化审阅结果。

**需求引用:**
- FR-03.1.1: 按维度生成审阅结果
- FR-03.1.2: 每条 ReviewFinding 必须关联至少一个 Evidence
- FR-03.1.3: 未关联 Evidence 的 Finding 标记为 UNVERIFIED

**设计引用:**
- [design/03-审阅生成.md#21-审阅生成服务](design/03-审阅生成.md#21-审阅生成服务)

**数据模型引用:**
- analysis_tasks, review_results, review_findings, finding_evidences

**实现要点:**
- 同论文 Evidence 稳定加载后结束只读事务；通过 EmbeddingClient 执行按维度精确 cosine Top-K，平分按 page_number/created_at/id 排序
- E1/E2 alias、安全 Prompt、严格 JSON 类型和维度校验
- Evidence 全有或全无绑定；UNVERIFIED Finding 公开过滤
- 多维度结果批次与 SUCCEEDED 状态原子提交，任一失败全部回滚
- MockLLMClient 作为默认离线实现；可配置 HuaweiMaaSLLMClient 使用 MaaS 标准 API V2 非流式推理

**验收标准:**
- 审阅结果含 Evidence 绑定
- UNVERIFIED Finding 不返回
- 无效 UUID、非法 options、跨用户资源与第二维失败路径均有 PostgreSQL API 测试

#### 任务 3.1.1b: Embedding 抽象与语义 Evidence 检索 ✅ DONE（P3.2）

**实现要点:**
- `EmbeddingClient.embed(texts)` 统一契约，严格验证数量、维度、有限数值和非零范数
- 默认 MockEmbeddingClient 离线确定性支持中英文词项；HuaweiMaaSEmbeddingClient 通过 HTTPS、Bearer、批处理和严格响应校验接入
- DB 候选加载与外部推理解耦；Evidence 每任务只向量化一次，各维度 query 保持请求顺序
- 任一批次、查询或外部推理失败时任务安全 FAILED，所有审阅结果、发现和关联均为 0
- 当前无 FAISS/pgvector、持久化缓存或 `PaperChunk.embedding_id` 回填

**验收结果:** P3.2 定向 `142 passed`；Docker 后端全量 `205 passed, 0 skipped`。

#### 任务 3.1.1c: Huawei MaaS 生成式模型适配器 ✅ DONE（P3.3）

**实现要点:**
- `LLMError` 统一配置、网络、HTTP、JSON 和响应结构错误，公开任务错误保持安全文案
- `HuaweiMaaSLLMClient` 仅允许绝对 HTTPS base URL，SecretStr 正确解包，发送 Bearer、`stream=false` 和 `max_completion_tokens`
- messages、单 choice/index 0、assistant/content 和 `finish_reason=stop` 严格校验；不接受多 choice、截断或工具调用响应
- 默认工厂保持 Mock，可按 `PAPERLENS_LLM_BACKEND=huawei_maas` 切换；无进程级可变测试单例
- Huawei MockTransport 成功结果经过既有严格审阅解析和真实 Evidence 绑定；首维/第二维失败均整批回滚，且 transport 调用点无活动 SQLAlchemy 事务
- 自动测试不访问公网，不代表用户账号、区域、模型质量或费用已经完成真实验收

**验收结果:** P3.3 定向 `73 passed`；Docker 后端全量 `277 passed, 0 skipped`。

#### 任务 3.1.2: 审阅结果前端页面（已完成）

**任务描述**: 实现审阅结果页面（P05），按维度展示 Finding，Evidence 追溯。

**需求引用:**
- FR-03.1.4: 支持 STRENGTH / WEAKNESS / SUGGESTION 类型
- FR-03.1.5: 评分 1-5，含 overall_verdict

**设计引用:**
- [design/07-前端展示.md#35-p05-审阅结果-reviewresultview--已实现](design/07-前端展示.md#35-p05-审阅结果-reviewresultview--已实现)
- [design/10-前端详细设计.md#45-p05-审阅结果-reviewresultview--已实现](design/10-前端详细设计.md#45-p05-审阅结果-reviewresultview--已实现)

**API 引用:**
- GET /api/v1/papers/{paper_id}/reviews
- POST /api/v1/papers/{paper_id}/tasks

**实现要点:**
- 审阅概览 + 维度卡片 + Finding 卡片
- Finding 类型标签颜色
- 证据链接跳转高亮
- 审阅任务轮询
- 历史结果按 task_id 归组，新任务完成前保留旧结果
- 轮询失败重试、timer 清理和旧响应失效

**验收标准:**
- 审阅结果按维度展示
- Finding 类型标签正确
- 证据链接跳转正常
- 前端 45 项组件测试通过，生产构建成功

---

## 4. 指标提取与口径判断（P4.1 后端已完成）

### 4.1 实验指标提取

**需求引用:**
- FR-04.1.1: 从 PaperTable 的 structured_data 中提取指标
- FR-04.1.2: 记录模型名、数据集名、指标名、指标值
- FR-04.1.3: 关联来源 Evidence 和表格行号

**设计引用:**
- [design/04-指标提取与口径判断.md#2-执行流程](design/04-指标提取与口径判断.md#2-执行流程)

**API 引用:**
- GET /api/v1/papers/{paper_id}/metrics

**数据模型引用:**
- metric_records

**验收标准:**
- 指标记录 API 返回结构化数据

#### 任务 4.1.1: 指标提取后端服务（已完成）

**任务描述**: 从论文表格和正文中提取实验指标。

**需求引用:**
- FR-04.1.1: 从 structured_data 中提取指标
- FR-04.1.2: 记录模型名、数据集名、指标名、指标值
- FR-04.1.3: 关联来源 Evidence 和表格行号

**设计引用:**
- [design/04-指标提取与口径判断.md#2-执行流程](design/04-指标提取与口径判断.md#2-执行流程)

**数据模型引用:**
- metric_records

**实现要点:**
- 从 structured_data 按行列提取
- 完全离线的确定性规则；百分号统一为 0～1
- 每条记录只关联 Evidence 或表格行之一，写入前校验同论文来源
- 来源快照结束读事务后解析，记录与任务成功状态原子提交

**验收标准:**
- 指标可提取并查询
- 关联 Evidence 和表格行号

#### 任务 4.1.2: Checkpoint 口径判断（已完成）

**任务描述**: 识别 final/max/mean/best 等统计口径并标注来源。

**需求引用:**
- FR-04.2.1: 基于规则引擎判断 checkpoint_type
- FR-04.2.2: 标注口径来源
- FR-04.2.3: LLM 仅辅助歧义消解

**设计引用:**
- [design/04-指标提取与口径判断.md#34-checkpoint](design/04-指标提取与口径判断.md#34-checkpoint)

**数据模型引用:**
- metric_records (checkpoint_type, checkpoint_source)

**实现要点:**
- 关键词匹配 + 上下文分析
- caption / row_header / context 完整关键词匹配
- 冲突或无证据统一 UNKNOWN，不按数值最大推断
- LLM 不参与候选、数值或口径生成

**验收标准:**
- 口径类型和来源正确标注
- LLM 不参与数值计算
- P4.1 定向 67 passed；Docker 后端 385 passed、0 skipped；Alembic 007 head

#### 任务 4.2.1: 指标分析前端页面（已完成）

**任务描述**: 实现指标分析页面（P06），指标表格，口径标注，筛选。

**需求引用:**
- FR-04.1.2: 记录模型名、数据集名、指标名、指标值

**设计引用:**
- [design/07-前端展示.md#36-p06-指标分析-metricanalysisview--已实现](design/07-前端展示.md#36-p06-指标分析-metricanalysisview--已实现)
- [design/10-前端详细设计.md#46-p06-指标分析-metricanalysisview--已实现](design/10-前端详细设计.md#46-p06-指标分析-metricanalysisview--已实现)

**API 引用:**
- GET /api/v1/papers/{paper_id}/metrics
- POST /api/v1/papers/{paper_id}/tasks

**实现要点:**
- 最新成功任务和历史成功任务均按 `task_id` 隔离
- 创建/恢复/轮询任务，活动期间保留上一轮成功结果
- 指标名、数据集、Checkpoint 后端筛选与分页
- 百分比显示、存储值、六类 Checkpoint 和原文展开
- Evidence 深链、表格来源信息和异常来源降级
- generation/request id 防止旧异步回写

**验收标准:**
- 指标表格正确渲染
- 筛选功能正常
- 证据链接跳转正常
- 快速交互不会发生旧响应覆盖，路由变化和卸载后 timer 已清理

---

## 5. 实验数据分析（P5.1 部分实现）

### 5.1 CSV/Excel 实验数据分析

**需求引用:**
- FR-05.1.1: 支持 CSV / XLSX / XLS 文件上传
- FR-05.1.2: 使用路径型确定性解析器识别数据结构
- FR-05.1.3: 使用确定性 Python 代码计算统计摘要
- FR-05.1.4: LLM 不参与任何数值计算

**设计引用:**
- [design/05-实验数据分析.md#1-p51-实验数据上传服务](design/05-实验数据分析.md#1-p51-实验数据上传服务)
- [design/05-实验数据分析.md#3-p52-统计与交叉验证规划](design/05-实验数据分析.md#3-p52-统计与交叉验证规划)

**API 引用:**
- POST /api/v1/papers/{paper_id}/experiment-files/upload
- GET /api/v1/papers/{paper_id}/experiment-files
- GET /api/v1/experiment-files/{file_id}
- GET result 与 DELETE 仍为后续规划

**数据模型引用:**
- experiment_files（CURRENT）；experiment_results（PLANNED）

**验收标准:**
- 实验数据文件可上传并解析
- P5.1 不计算统计摘要；P5.2 必须由确定性代码计算

#### 任务 5.1.1: 实验数据上传与结构解析（✅ DONE）

**任务描述**: 实现 CSV/XLSX/XLS 文件上传和解析。

**需求引用:**
- FR-05.1.1: 支持 CSV / XLSX / XLS 文件上传
- FR-05.1.2: 使用路径型确定性解析器识别列结构

**设计引用:**
- [design/05-实验数据分析.md#1-p51-实验数据上传服务](design/05-实验数据分析.md#1-p51-实验数据上传服务)

**数据模型引用:**
- experiment_files

**实现要点:**
- 固定块临时落盘和实际字节限制（20MB）
- CSV 确定性编码/分隔符解析、XLSX ZIP 安全、XLS OLE 校验
- version=1 `columns_info` JSONB、严格 Pydantic 响应和公开哈希隐藏
- 同用户/论文/哈希幂等及数据库并发收口
- storage/flush/commit 回滚补偿和离线保证

**验收标准:**
- CSV/XLSX/XLS 可上传并解析
- 新建 201、重复 200；并发最终一行一对象
- 结构列表和详情只允许资源所属用户访问

#### 任务 5.1.2: 统计摘要计算（规划）

**任务描述**: 使用确定性 Python 代码计算统计摘要。

**需求引用:**
- FR-05.1.3: 使用确定性 Python 代码计算统计摘要
- FR-05.1.4: LLM 不参与任何数值计算

**设计引用:**
- [design/05-实验数据分析.md#3-p52-统计与交叉验证规划](design/05-实验数据分析.md#3-p52-统计与交叉验证规划)

**数据模型引用:**
- experiment_results (summary_stats)

**实现要点:**
- pandas 计算count/mean/std/min/max/median
- LLM 不参与计算
- summary_stats JSONB 存储

**验收标准:**
- 统计摘要正确计算
- LLM 不参与数值计算

### 5.2 指标交叉验证

**需求引用:**
- FR-05.2.1: 匹配论文 MetricRecord 与实验数据中的指标
- FR-05.2.2: 计算偏差值（diff）
- FR-05.2.3: 标记验证状态（MATCH / MISMATCH）

**设计引用:**
- [design/05-实验数据分析.md#3-p52-统计与交叉验证规划](design/05-实验数据分析.md#3-p52-统计与交叉验证规划)

**数据模型引用:**
- experiment_results (metric_comparisons)

**验收标准:**
- 交叉验证结果可查询

#### 任务 5.2.1: 指标交叉验证实现（规划）

**任务描述**: 对比论文报告指标与实验数据指标，标记偏差。

**需求引用:**
- FR-05.2.1: 匹配论文 MetricRecord 与实验数据
- FR-05.2.2: 计算偏差值
- FR-05.2.3: 标记验证状态

**设计引用:**
- [design/05-实验数据分析.md#3-p52-统计与交叉验证规划](design/05-实验数据分析.md#3-p52-统计与交叉验证规划)

**数据模型引用:**
- experiment_results (metric_comparisons)

**实现要点:**
- 匹配 MetricRecord 与实验数据
- diff = paper_value - experiment_value
- MATCH / MISMATCH 标记

**验收标准:**
- 交叉验证结果可查询

#### 任务 5.2.2: 实验数据前端页面（规划）

**任务描述**: 实现实验数据页面（P07），文件上传，统计摘要，交叉验证。

**需求引用:**
- FR-05.1.1: 支持 CSV / XLSX / XLS 文件上传

**设计引用:**
- [design/07-前端展示.md#37-p07-实验数据-experimentdataview--规划](design/07-前端展示.md#37-p07-实验数据-experimentdataview--规划)
- [design/10-前端详细设计.md#47-p07-实验数据-experimentdataview--规划](design/10-前端详细设计.md#47-p07-实验数据-experimentdataview--规划)

**API 引用:**
- POST /api/v1/papers/{paper_id}/experiment-files/upload
- GET /api/v1/papers/{paper_id}/experiment-files
- GET /api/v1/experiment-files/{file_id}/result

**实现要点:**
- 拖拽上传区
- 文件列表表格
- 统计摘要表格
- MATCH/MISMATCH 状态标签

**验收标准:**
- 文件上传和列表正常
- 统计摘要正确展示
- 交叉验证结果正确

---

## 6. 报告导出（规划）

### 6.1 审稿报告导出

**需求引用:**
- FR-06.1.1: 生成包含审阅结果、指标记录的报告
- FR-06.1.2: 支持 Markdown 格式导出
- FR-06.1.3: 支持中英文语言选择

**设计引用:**
- [design/06-报告导出.md#21-报告生成服务](design/06-报告导出.md#21-报告生成服务)

**API 引用:**
- POST /api/v1/papers/{paper_id}/exports
- GET /api/v1/exports/{export_id}
- GET /api/v1/exports/{export_id}/download

**数据模型引用:**
- export_reports

**验收标准:**
- 报告可导出下载

#### 任务 6.1.1: Markdown 报告生成（规划）

**任务描述**: 实现 Markdown 格式审阅报告生成。

**需求引用:**
- FR-06.1.1: 生成包含审阅结果、指标记录的报告
- FR-06.1.2: 支持 Markdown 格式导出
- FR-06.1.3: 支持中英文语言选择

**设计引用:**
- [design/06-报告导出.md#21-报告生成服务](design/06-报告导出.md#21-报告生成服务)
- [design/06-报告导出.md#22-markdown-报告模板](design/06-报告导出.md#22-markdown-报告模板)

**数据模型引用:**
- export_reports

**实现要点:**
- Markdown 模板拼接
- 中英文语言选择
- 异步生成 + HTTP 轮询

**验收标准:**
- Markdown 报告可生成和下载
- 中英文语言正确

#### 任务 6.1.2: PDF/DOCX 报告导出（规划）

**任务描述**: 支持 PDF 和 DOCX 格式报告导出。

**需求引用:**
- FR-06.2.1: 支持 PDF 格式导出
- FR-06.2.2: 支持 DOCX 格式导出

**设计引用:**
- [design/06-报告导出.md#21-报告生成服务](design/06-报告导出.md#21-报告生成服务)

**数据模型引用:**
- export_reports

**实现要点:**
- Markdown → PDF 转换
- Markdown → DOCX 转换
- 异步生成 + HTTP 轮询

**验收标准:**
- PDF/DOCX 报告可生成和下载

#### 任务 6.1.3: 报告导出前端页面（规划）

**任务描述**: 实现报告导出页面（P08），导出配置，进度轮询，下载。

**需求引用:**
- FR-06.1.1: 生成包含审阅结果、指标记录的报告

**设计引用:**
- [design/07-前端展示.md#38-p08-报告导出-reportexportview--规划](design/07-前端展示.md#38-p08-报告导出-reportexportview--规划)
- [design/10-前端详细设计.md#48-p08-报告导出-reportexportview--规划](design/10-前端详细设计.md#48-p08-报告导出-reportexportview--规划)

**API 引用:**
- POST /api/v1/papers/{paper_id}/exports
- GET /api/v1/exports/{export_id}
- GET /api/v1/exports/{export_id}/download

**实现要点:**
- 导出配置: 格式、语言、包含选项
- 生成按钮 + 导出历史
- 3 秒轮询进度
- 下载按钮

**验收标准:**
- 导出配置正常
- 进度轮询正常
- 下载功能正常

---

## P4.3 华为云 MaaS LLM 运行配置任务

| 任务 | 状态 |
|------|------|
| Compose 安全开关和 LLM 单项透传 | ✅ DONE |
| Embedding 费用隔离 | ✅ DONE |
| 离线 config-check | ✅ DONE |
| 显式付费确认烟测 | ✅ DONE |
| 配置/CLI/Compose/Huawei LLM 离线测试 | ✅ 110 passed / 0 skipped |
| 全量回归和运行验收 | ✅ 后端 435/0 skipped；前端 106；构建成功 |
| 用户真实 MaaS 小额烟测 | ✅ 第二次且最后一次授权请求成功，35 字符；首轮安全失败后未自动重试 |

**文档版本**: v1.1
**创建日期**: 2026-07-13
**最后更新**: 2026-07-14
