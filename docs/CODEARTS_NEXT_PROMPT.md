# 码道下一阶段提示词：P2.4 事务边界与验收收口

> 复制下面代码框中的全部内容，粘贴到华为云码道“智能体 / 规范开发”模式。

~~~text
继续修复 D:\shixi\PaperLens 项目。

本轮定义为 P2.4：修复 P2.3 遗留的事务边界、测试库冷启动、资源关闭和前端轮询/高亮降级问题，完成 P2 解析闭环的最后收口。

P2.3 的数据库隔离主目标已经真实生效。外部独立复测结果：

```text
Docker backend pytest: 46 passed, 0 skipped
frontend Vitest:        11 passed
frontend build:         success
开发库 papers:          测试前 25，测试后 25
测试库 papers:          测试后 0
alembic check:          No new upgrade operations detected
```

不要推翻或重复重写已经正确的测试库 Engine 隔离方案。但代码审查确认仍有数个运行级缺陷和弱断言，P2 暂不能结束。禁止开始 P3、LLM、MaaS/ModelArts、FAISS、指标提取、Excel 或报告导出。

开始前完整阅读：

- docs/PROGRESS.md
- backend/paperlens/core/database.py
- backend/paperlens/api/papers.py
- backend/paperlens/services/pdf_parser.py
- backend/tests/conftest.py
- backend/tests/test_api/test_health.py
- backend/tests/test_services/test_pdf_parser.py
- frontend/src/views/PaperDetailView.vue
- frontend/src/tests/PaperDetailView.test.ts
- docker-compose.yml
- README.md
- docs/IMPLEMENTATION_STATUS.md
- docs/api-contract.md
- docs/architecture.md
- docs/data-model.md
- docs/security-design.md

先给出简短计划，然后直接实施。所有测试必须验证真实行为，禁止只增加测试名称或放宽断言。

一、真正保证 UploadFile 和临时文件在所有路径关闭

当前 `upload_paper()` 仍有明确缺陷：

```python
filename = _sanitize_filename(raw_filename)

if not filename.lower().endswith(".pdf"):
    raise AppError(...)

try:
    ...
```

扩展名错误发生在 `try/finally` 之外，因此服务端 UploadFile 没有执行 `await file.close()`。另外，读取循环异常时 NamedTemporaryFile 句柄也不一定先关闭，外层代码就尝试删除路径。

要求：

1. 将扩展名校验也纳入最外层资源管理边界。
2. UploadFile 在以下每条路径都必须且只能关闭一次：
   - 非 PDF 扩展名
   - PDF 扩展名但魔数错误
   - 文件超过业务上限
   - `await file.read()` 抛异常
   - hash 计算异常
   - storage.save 异常
   - DB commit 异常
   - 正常上传并交给 BackgroundTasks
3. NamedTemporaryFile 使用明确的 context/finally 管理，任何异常发生前先关闭句柄，再删除文件。
4. 未成功交给后台任务的临时文件必须由请求路径删除；已成功交给后台任务的临时文件只能由 `_process_paper()` 最终删除。
5. storage.save 成功但后续 Paper 构造、DB commit 或响应构造失败时，存储对象不能遗留。删除失败要记录 warning，不能静默 `pass`。
6. 增加直接针对服务端 UploadFile 的单元测试或可靠 spy。仅关闭客户端上传文件句柄不能证明服务端 `UploadFile.close()` 被调用。
7. 每个资源测试严格断言 close 调用次数和临时路径不存在，不能只断言 HTTP 状态码。

二、修复测试数据库“已存在时可用、缺失时无法创建”的冷启动问题

当前 `_ensure_test_database()` 先连接 `paperlens_test`，再检查该数据库是否存在：

```python
conn = psycopg2.connect(test_database_url)
SELECT 1 FROM pg_database ...
CREATE DATABASE paperlens_test
```

如果 `paperlens_test` 根本不存在，第一步连接已经失败，无法执行 CREATE DATABASE。更早的 `_db_available()` 也会返回 false，使集成测试直接 skip，`_ensure_test_database()` 根本不会运行。

要求：

1. 测试库确保逻辑必须连接维护库 `postgres` 或已知存在的开发库，只使用同一 host/user/password，然后查询并幂等创建 `paperlens_test`。
2. 创建完成后再连接 `paperlens_test`、执行 Alembic upgrade head、校验 revision。
3. Docker 强制模式不得在 `_db_available()` 阶段因为测试库尚不存在而 skip。
4. 在 docker-compose backend 环境中显式增加：

```text
PAPERLENS_REQUIRE_TEST_DB=true
```

5. 当强制模式为 true 时，缺失 TEST URL、数据库名不是严格的 `paperlens_test`、创建失败、迁移失败或连接失败都必须 fail，禁止 skip。
6. 宿主机没有 PostgreSQL 时仍可诚实 skip integration 测试，但 Docker 全量测试必须 0 skipped。
7. 不要通过删除当前 `paperlens_test` 或 PostgreSQL volume 来测试冷启动。使用 mock、独立辅助函数测试，或创建和删除一个不会碰业务数据的专用临时数据库名；任何临时数据库操作必须有严格命名守卫。
8. 测试库初始化代码应放在可复用 helper/fixture 中，不要把数据库管理逻辑继续堆在 `test_health.py`。

三、测试清理必须 fail-closed，禁止继续吞异常

当前 `_truncate_test_tables()` 有两层静默异常：

```python
for t in tables:
    try:
        TRUNCATE ...
    except Exception:
        pass
...
except Exception:
    pass
```

这意味着清理失败后测试仍会显示通过，残留数据可能污染后续测试。

要求：

1. 删除所有 cleanup `except: pass`。
2. fixture 使用 `try/finally`，无论测试通过或失败都执行清理。
3. 优先使用一条 `TRUNCATE table1, table2, ... CASCADE`，或从 SQLAlchemy metadata/数据库 schema 安全获得业务表集合，避免逐表失败后继续。
4. 清理连接和 cursor 也必须用 context manager/finally 关闭。
5. 清理失败必须让测试 session 明确失败，并输出数据库名和原始异常。
6. 清理前后都严格断言当前数据库名为 `paperlens_test`；禁止对开发库执行 TRUNCATE。
7. 清理结束后查询所有业务表，严格断言无测试残留；至少不能只查 papers 一张表。
8. 增加 cleanup 失败测试，证明异常不会被吞掉。

四、修复 PaperTable 降级时回滚整篇论文的问题

当前 `_process_paper()` 对每张表执行 `db.flush()`，失败后调用：

```python
db.rollback()
```

这会回滚当前整个事务，连此前已加入的 PaperPage、PaperSection、PaperChunk 也一起撤销。随后代码继续添加 Evidence，而 `chunk_id_map` 仍引用已回滚的 chunk ID，最终可能导致外键失败并把整篇论文标为 FAILED。该实现不是“表格失败可降级”。

要求：

1. 表格单项失败只能回滚该表格，不能回滚页面、章节、分块和其他表格。
2. 使用 `db.begin_nested()`/SAVEPOINT 或先完成严格数据验证后跳过非法表格；禁止在表格循环的局部异常中调用整个 Session 的 `rollback()`。
3. 单张表失败后：
   - 论文仍可 PARSED
   - PaperPage/PaperSection/PaperChunk/Evidence 均正常保存
   - 合法表格正常保存
   - 仅非法表格被跳过
   - warning 日志包含 paper_id、page_number、table_index
4. 如果页面/章节/分块/Evidence 等核心数据失败，仍应回滚整篇解析并将 Paper 标为 FAILED。
5. 增加真实 PostgreSQL 集成测试：受控 mock `parse_pdf()` 返回页面、章节、分块、Evidence、一个合法表格和一个违反约束的表格，严格断言上述降级行为。
6. 测试必须能在旧实现上失败，不能只直接调用 bbox 交换代码。

五、修正后端仍然存在的弱断言

当前 Evidence 详情测试包含永远为真的断言：

```python
assert detail["char_start"] is not None or detail["char_start"] is None
assert detail["char_end"] is not None or detail["char_end"] is None
```

它没有严格验证 bbox、char range、section_id 和 chunk_id，与 P2.3 汇报不一致。

要求：

1. 删除所有恒真断言。
2. Evidence 详情测试确定性插入完整字段值，严格逐字段比较：
   - id
   - quoted_text
   - page_number
   - bbox_x0/y0/x1/y1
   - char_start/char_end
   - evidence_type
   - section_id
   - chunk_id
3. 另设 nullable 字段测试，不要把 nullable 和完整字段测试混在一起。
4. error_message 安全测试必须注入包含真实内部信息模式的异常，例如：

```text
/tmp/private/source.pdf
C:\secret\source.pdf
postgresql://user:password@host/db
SELECT * FROM secret_table
Traceback ...
```

严格断言数据库和 API 均只包含安全映射后的中文消息，不包含任何注入内容。
5. 为非 PDF 扩展名、读取异常、临时文件清理、表格 SAVEPOINT、cleanup 失败分别增加能失败的行为测试。
6. 整理重复的“等待 Paper 终态”代码为有超时、返回终态并在超时/FAILED 时给出明确信息的 helper。

六、修复前端降级提示、Evidence 导航和轮询定时器

当前 PaperDetailView 仍有以下问题：

1. `highlightDegraded` 只在 char_start/char_end 为 null 时为 true。offset 越界或切片与 quoted_text 不一致时，`highlightRange` 返回 null，但不会显示“该证据暂不支持精确高亮”。
2. `retryPoll()` 直接调用 `load()`，但原有 interval 在轮询失败时没有停止。重试后可能再创建一个 interval，造成重复轮询和计时器泄漏。
3. `load()` 每次看到 PROCESSING 都直接 `setInterval()`，没有先清理既有 timer。
4. 点击当前页 Evidence 时 `isNavigatingToEvidence = true`，但 currentPage 没变化，watcher 不会复位该标志；后续普通跳页可能被错误当成 Evidence 导航。
5. 切换到页面 Tab 的 watcher和 `goToEvidence()` 都可能调用 `loadPage()`，造成重复请求。

要求：

1. 只要已选择 Evidence 且无法形成严格匹配的 highlightRange，包括 null、越界、start>=end、文本 mismatch，都显示统一降级提示，且不渲染 mark。
2. 抽取 `stopPolling()` 和 `startPolling()`：任何时刻最多一个 timer。
3. 轮询失败时停止当前 timer，再显示错误；点击重试先清理旧 timer，再立即请求一次，根据结果决定是否重新开始轮询。
4. PROCESSING → PARSED/FAILED、详情重新加载、组件卸载时都必须停止 timer。
5. 重构页面导航为单一入口，普通翻页/跳页清除 Evidence，Evidence 导航保留 Evidence；不要依赖可能残留的布尔标志。
6. 每次用户动作只请求一次目标页。tab watcher、page watcher 和 goToEvidence 不得竞争发请求。
7. 继续保留 pageRequestId 或等价的陈旧响应防护。

七、把 11 项前端测试改为真实验收测试

当前测试仍有以下缺口：

1. 页面错误测试只检查“重试”按钮存在，没有点击重试并验证恢复。
2. 初始详情失败测试也没有点击重试。
3. mismatch 测试只断言没有 mark，没有断言降级提示存在。
4. rapid evidence 测试顺序等待每个请求完成，没有制造“旧请求晚于新请求返回”，因此没有验证 pageRequestId。
5. 没有轮询失败 → 点击重试 → 只有一个 timer 的测试。
6. XSS mock 使用字符串 `&amp;`，没有验证原始 `&` 字符的显示。

要求新增或重写严格测试：

1. 页面加载失败后点击重试，断言第二次 getPage 成功、错误消失、页面内容出现。
2. 初始 getPaper 失败后点击重试，断言论文详情、章节和 Evidence 正常加载。
3. mismatch、越界和 null range 三种情况都断言：降级提示存在、mark 不存在。
4. 使用可控 deferred Promise：先请求第 1 页，再请求第 2 页；让第 2 页先返回、第 1 页后返回，最终 DOM 必须仍显示第 2 页及其高亮。
5. 同一 Evidence 导航严格断言目标 `getPage()` 调用一次，禁止仅使用 `toHaveBeenCalledWith`。
6. 轮询失败后断言旧 timer 已停止；点击重试后任意时刻只有一个 timer；PARSED 后 timer 清零且不再调用 API。
7. XSS 文本包含原始 `<script>`、`<b>`、`<`、`>`、`&`，断言无可执行元素、无双重转义字面量、原始可读字符存在。
8. 每项测试结束恢复 fake timers 并 unmount，避免测试间泄漏。

八、完成文档同步

P2.3 后文档仍有未同步项：

1. docs/IMPLEMENTATION_STATUS.md 的 P7-01“论文上传页面”仍标为未开始，但 UploadView 已实现。
2. P7-02 将“审阅结果展示”和“Evidence 高亮”混在一个条目中；审阅结果尚未实现，但论文详情、页面与 Evidence 高亮已经部分实现，应拆分或标为部分完成。
3. README 没有明确记录 Nginx 60MB 代理上限与后端 50MB 业务上限。
4. README/文档没有清楚说明测试强制使用 paperlens_test 以及清理失败会使测试失败。
5. architecture/security-design 中 FAISS 描述容易被读成当前实现，应明确标注为规划方案。

同步以下文件：

- README.md
- docs/IMPLEMENTATION_STATUS.md
- docs/api-contract.md
- docs/architecture.md
- docs/data-model.md
- docs/security-design.md
- docs/PROGRESS.md

要求：

1. 如实标记已实现、部分实现和未实现功能。
2. 明确当前前端只展示 normalized 文本高亮，不是 PDF.js bbox 覆盖层。
3. 明确 FAISS、LLM 审阅、指标提取、实验数据分析和报告导出均未实现。
4. “当前验证结果”使用本轮最新实测数据；历史阶段数据可以保留但不能与当前表混淆。

九、真实验证

完成后重新构建容器并独立复测，禁止沿用旧输出：

```powershell
cd D:\shixi\PaperLens
docker compose up --build -d
docker compose ps
docker compose logs --tail 200
```

记录开发库测试前数量：

```powershell
docker compose exec -T postgres psql -U paperlens -d paperlens -Atc "SELECT count(*) FROM papers"
```

运行：

```powershell
docker compose exec -T backend python -m pytest -q -rs
docker compose exec -T backend alembic current
docker compose exec -T backend alembic check
cd frontend
npm test -- --run
npm run build
```

验收要求：

1. Docker backend：0 failed、0 errors、0 skipped。
2. 测试前后开发库 papers 数量严格相等。
3. 测试库所有业务表清理后无测试残留。
4. 非 PDF 扩展名等所有上传路径均证明服务端 UploadFile 已关闭。
5. 受控非法表格只被跳过，论文仍 PARSED，核心解析数据完整。
6. cleanup 失败测试证明异常不会被吞掉。
7. 前端页面/详情重试真正恢复。
8. 轮询始终最多一个 timer。
9. 陈旧页面响应不能覆盖最后选择。
10. mismatch/越界/null 均显示降级提示。
11. Alembic 无未生成差异。
12. 通过 `http://localhost:3000` 完成一次真实 PDF 上传 → PARSED → Evidence → 跨页高亮回归。

任何失败必须修复并重新执行对应验证，不得仅记录失败后结束。

十、范围限制与汇报

本轮只完成 P2.4，不进入 P3，不实现 FAISS 或 LLM。

不得修改：

```text
.arts/
.codeartsdoer/
.git/
```

不要 git commit，不写入真实密钥，不删除数据库 volume，不自动清理无法确认归属的开发库记录。

完成后在 docs/PROGRESS.md 末尾追加 `P2.4 — 事务边界与验收收口`，必须如实记录：

- 开发库测试前后数量
- 测试库冷启动与强制守卫验证
- 测试库全业务表清理结果
- UploadFile 每条路径的关闭验证
- 临时文件与存储对象清理验证
- PaperTable SAVEPOINT 降级结果
- 后端通过/失败/跳过数量
- 前端测试数量及新增的严格场景
- 轮询 timer 数量验证
- 陈旧请求防护验证
- 前端构建结果
- 文档状态修正
- 尚未完成项

禁止把 skip、恒真断言、未点击的重试按钮、未制造乱序的并发测试或被吞掉的异常计为验证通过。
~~~
