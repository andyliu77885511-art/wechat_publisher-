QA 验收测试报告 - 公众号自动发布工具
测试日期：2026-04-22
测试人：AK-CEO（代执行）

==============================
一、测试结果汇总
==============================

语法检查：10/10 文件全部通过 py_compile
Import 依赖链：全部符号存在，可正常导入
接口签名：app.py 调用参数与模块定义匹配

发现问题：5个（P0x1, P1x1, P2x2, P3x1）

==============================
二、问题清单
==============================

[P0-001] 数据库路径不一致（阻塞）
------
描述：database.py 中 DB_PATH = os.getenv("DATA_DIR", "./data") + "/publisher.db"，
而 config.py 中 DB_PATH = os.path.join(BASE_DIR, "wechat_publisher.db")。
app.py 调用 database.init_db()，用的是 database.py 的路径（./data/publisher.db）。
init_db.py 用的是 config.DB_PATH（项目根目录/wechat_publisher.db）。
影响：运行 init_db.py 初始化的是一个数据库文件，app.py 运行时操作另一个数据库文件，数据完全隔离。
修复建议：database.py 中改为 import config; DB_PATH = config.DB_PATH
状态：已修复

[P1-001] 模块功能重复（严重）
------
描述：core/file_handler.py 和 core/media.py 存在重复函数：
- save_uploaded_file：file_handler 返回 tuple(str,str)，media 返回 Path
- extract_audio：两个文件都有，输出格式不同（mp3 vs wav）
- get_audio_path / get_audio_duration 功能重叠
影响：维护两份代码容易产生分歧，新开发者不知道该用哪个。app.py 当前用的是 file_handler，media.py 完全没被引用。
修复建议：删除 core/media.py 或将其合并到 file_handler.py，统一入口。
状态：已修复（media.py 标记废弃）

[P2-001] init_db 函数重复
------
描述：database.py 中 init_db() 是精简版（只建表），init_db.py 中 init_db() 是完整版（表+索引+触发器）。app.py 调用的是 database.py 的精简版，导致缺少索引和 updated_at 自动触发器。
影响：不影响功能正确性，但数据量增长后查询性能下降，updated_at 字段需要代码手动维护。
修复建议：database.py 的 init_db() 直接调用 init_db.py 的逻辑，或合并 DDL。
状态：已修复

[P2-002] .env.example 缺少字段
------
描述：.env.example 中缺少 OUTPUT_DIR 和 DB_PATH 两个配置项。config.py 中有对这两个环境变量的读取。
影响：用户配置时可能遗漏，不影响运行（有默认值），但不规范。
修复建议：补充到 .env.example。
状态：已修复

[P3-001] requirements.txt 多余依赖
------
描述：ffmpeg-python、markdown、Pillow 三个包在代码中均未直接 import。ffmpeg 是通过 subprocess 调用系统命令。markdown 和 Pillow 当前未使用。
影响：安装时多下载无用包，不影响功能。
修复建议：移除 ffmpeg-python，保留 markdown 和 Pillow 备用（后续可能需要），或加注释说明。
状态：建议项，暂不处理

==============================
三、已修复内容
==============================

1. database.py：DB_PATH 改为引用 config.DB_PATH
2. database.py：init_db() 增加索引和触发器，与 init_db.py 对齐
3. core/media.py：文件头添加废弃标注，不再被任何模块引用
4. .env.example：补充 OUTPUT_DIR 和 DB_PATH 字段

==============================
四、结论
==============================

修复 P0 和 P1 后，项目代码结构完整，模块接口一致，可以进入集成测试阶段。
建议下一步：配置真实 .env 密钥后做端到端联调。
