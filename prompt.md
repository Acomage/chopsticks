你是一个经验丰富的 Python 架构工程师兼开发者，请严格按照以下需求为我编写完整代码。

### 背景

我要开发一个轻量级的 **配置管理工具**，类似极简版的包管理器。
功能：

* 每个包定义在一个 `pkg.py` 文件里，里面有一个 `pkg: Package` 对象。
* `Package` 包含 `name, version, dependencies, install, uninstall, update` 等信息。
* `Action` 是一个抽象类，代表可以执行的操作（如创建文件、删除文件、执行命令等）。
* 我有一个 Git 仓库保存所有包目录，每个包一个文件夹。
* 本地用一个 JSON 文件保存已安装包和版本。
* 支持 **滚动更新**（始终使用最新版）。

---

### 项目结构

```
configmgr/
├── core/
│   ├── action.py        # 抽象 Action + 具体 Action 子类
│   ├── package.py       # Package 类
│   ├── executor.py      # 执行 Action，带回滚
│   ├── state.py         # 已安装状态管理
│   ├── depsolver.py     # 依赖解析（拓扑排序）
│   └── errors.py        # 自定义异常
│
├── repo/
│   ├── loader.py        # 加载 pkg.py -> Package
│   ├── gitutils.py      # git 操作（subprocess）
│
├── utils/
│   ├── fs.py            # 文件系统工具
│   ├── sysutils.py      # systemd / ufw / shell 工具
│
├── cli/
│   └── main.py          # 命令行接口
│
├── config.py            # 全局配置
└── __main__.py          # 入口
```

---

### 模块职责 & API 约定

#### `core/action.py`

```python
class Action(ABC):
    def check(self) -> bool: ...
    def run(self) -> None: ...
    def rollback(self) -> None: ...

class CreateFile(Action): ...
class DeleteFile(Action): ...
class CreateDir(Action): ...
class DeleteDir(Action): ...
class CreateLink(Action): ...
class DeleteLink(Action): ...
class AppendFile(Action): ...
class RemoveLastLine(Action): ...
class SystemdStart(Action): ...
class SystemdStop(Action): ...
class UfwAllow(Action): ...
class UfwDeny(Action): ...
class RunCommand(Action): ...
class RunShell(Action): ...
```

#### `core/package.py`

```python
class Package:
    def __init__(self, name, version, dependencies, install, uninstall, update): ...
```

#### `core/executor.py`

* 批量执行 `Action`，失败时回滚。

#### `core/depsolver.py`

* 输入：目标包名列表，`repo_lookup(name) -> Package`，`installed: dict`
* 输出：拓扑排序后的安装顺序。
* 支持滚动更新（如果已安装且版本旧，则执行 update）。

#### `core/state.py`

* 保存/读取 JSON 状态。

#### `repo/loader.py`

* 加载 `pkg.py` 文件，返回 `Package` 对象。

#### `repo/gitutils.py`

* 封装 `git pull`、`git show` 等操作。

#### `cli/main.py`

* CLI 入口，支持 `install/uninstall/list/update`。

---

### 要求

1. 代码必须完整、可运行。
2. 不要使用标准库以外的依赖。
3. Python 3.11+ 特性可以用。
4. 输出时，请 **按文件分块**，标明文件路径。
5. 先写最小可运行 Demo（实现 `install` + `list`）。
6. 然后扩展到完整功能。

---

### 示例

用户在 `repo/nginx/pkg.py` 里定义：

```python
from core.package import Package
from core.action import RunCommand

pkg = Package(
    name="nginx",
    version="1.28.0",
    dependencies=["python"],
    install=[RunCommand("echo install nginx")],
    uninstall=[RunCommand("echo uninstall nginx")],
    update=[RunCommand("echo update nginx")]
)
```

运行：

```bash
$ python -m configmgr install nginx
Installing python-3.12.0
install python
Installing nginx-1.28.0
install nginx
```

---

请按以上规范，逐步输出完整代码。

