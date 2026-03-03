# 艾利特 CS625 ROS 2 控制与视觉集成项目

本项目包含艾利特（Elite）CS625 协作机器人控制与视觉集成的全链路 ROS 2 应用。**重磅特性在于并存的“双控制架构”**：兼容社区主流的 MoveIt+ros2_control 规划路径，以及面向工业集成的高效 TCP 桥接路径，极大提升了系统灵活性和适用性。

---

## 1. 系统环境与配置

| 项目         | 版本 / 配置            | 备注                    |
| ------------ | -------------------- | ---------------------  |
| 操作系统     | Ubuntu 22.04 LTS     | 推荐物理机/VMWare虚拟机  |
| ROS 2 版本   | Jazzy Jalisco        | Desktop Install        |
| 机器人型号   | Elite CS625          |                        |
| 虚拟机      | VMWare Virtual Platform | 可选                   |
| Git         | ≥ 2.34.1             |                        |

---

## 2. 网络设置

- **虚拟机网络方式**：推荐桥接模式，确保机器人控制器-PC-外部网络同一网段。
- **IP 示例分配**：
    - 机器人控制器：`192.168.1.200`（静态）
    - 本机：`192.168.1.102`（或同网段）
    - 子网掩码：`255.255.255.0`
- **物理连接要求**：PC和机器人须直连或同路由器。
- **Ping 验证**：`ping 192.168.1.200`，返回正常说明连通。

---

## 3. 安装与部署

1. **克隆本仓库**
    ```bash
    cd ~
    git clone https://github.com/addission/elite_robot_project_20260303.git elite_ros_ws
    ```

2. **安装依赖并编译**
    ```bash
    cd ~/elite_ros_ws
    sudo apt update
    rosdep install --from-paths src -y --ignore-src
    colcon build
    ```

3. **（推荐）配置桌面快捷启动器**
    ```bash
    cp ~/elite_ros_ws/desktop_files/CS625机器人启动器.desktop ~/Desktop/
    chmod +x ~/Desktop/CS625机器人启动器.desktop
    # 直接双击桌面图标即可一键启动全系统
    ```

---

## 4. 系统架构图与数据流

本系统实现**两条并行的控制通路**，如下图所示：

<details>
<summary>点击展开查看 Mermaid 交互数据流系统图（如 GitHub 不支持，可用 Typora/Obsidian 或 VSCode Markdown Preview 插件查看）</summary>

```mermaid
graph TD

    subgraph "用户/外部系统"
        U[用户]
        V(外部视觉/控制程序)
    end

    subgraph "PC端ROS2 (elite_ros_ws)"
        subgraph "路径二：TCP桥接"
            V -- "TCP:9999 指令" --> TCP[tcp_server.py]
            TCP -- "/target_pose" --> RC[robot_commander.py]
            TCP -- "/target_pose" --> TFBC[pose_to_tf_broadcaster.py]
            TCP -- "/target_pose" --> SMP[static_model_publisher.py]
            RC -- "TCP:60000 指令" --> SCRIPT(external_control.script)
        end
      
        subgraph "路径一：MoveIt+ros2_control"
            U -- "RViz界面操作" --> RVZ[RViz2]
            RVZ -- "规划Goal" --> MG[move_group]
            MG -- "轨迹Action" --> AC[arm_controller]
            AC -- "关节命令" --> R2C[ros2_control 控制器]
            R2C -- "硬件I/O" --> HI[EliteCSPositionHardwareInterface]
        end

        RVZ -- "场景反馈/TF" -->|反馈| MG
        HI -- "/joint_states, TF" --> RVZ
        TFBC -- "TF world->slot_origin" --> RVZ
        SMP -- "Marker" --> RVZ
    end

    subgraph "机器人硬件"
        HI -- "网络 I/O" --> R(CS625 控制器)
        SCRIPT -- "movel/movej 执行" --> R
    end
```
</details>

---

## 5. 目录结构与关键功能（精选解读）

```text
elite_ros_ws/
├── src/
│   ├── tcp_bridge/                   # 路径二核心: 视觉/外部控制-ROS-TCP桥
│   │   ├── tcp_server.py             # 接收9999端口的TCP指令，发布/target_pose
│   │   ├── robot_commander.py        # 订阅/target_pose, TCP 60000发往机器人
│   │   ├── pose_to_tf_broadcaster.py # 辅助: 将/target_pose变为TF
│   │   └── static_model_publisher.py # 辅助: 显示目标模型Marker
│   ├── eli_cs_robot_description/     # 机器人模型及配置
│   │   ├── urdf/cs625.urdf.xacro     # 顶层宏，自动加载所有参数和mesh
│   │   ├── config/cs625/             # 所有关节/动力学/视觉参数
│   ├── eli_cs_robot_driver/          # 路径一硬件驱动/控制器
│   │   ├── config/cs625_controllers.yaml # ros2_control控制器参数
│   │   ├── src/ & include/           # C++驱动、硬件协议层、控制插件
│   ├── elite_cs625_moveit_config/    # MoveIt标准配置
│   │   ├── config/cs625.srdf         # 规划组/禁用碰撞体
│   │   ├── config/kinematics.yaml    # IK配置
│   │   └── launch/move_group.launch.py # 启动MoveIt主节点
│   ├── ...
```

---

## 6. 双路径端到端流程详解

### 6.1 标准 MoveIt + ros2_control 路径（复杂规划/避障）

1. **RViz手动交互** → 拖动Goal → “Plan & Execute”
2. **move_group** 接受规划请求，收集/joint_states/场景，调用OMPL进行路径优化
3. **move_group** 生成轨迹，发往 arm_controller（通过 FollowJointTrajectory Action）
4. **ros2_control** -> EliteCSPositionHardwareInterface 插件 → 网络下发到机器人执行器
5. **机器人物理执行**，实时反馈/joint_states/TF → RViz

### 6.2 TCP视觉桥快捷直控路径（外部感知/精确点控/视觉引导等）

1. **外部系统** TCP发送指令到 `tcp_server.py`（9999端口）
2. **tcp_server.py** 解析为/target_pose（PoseStamped消息）广播
3. **pose_to_tf_broadcaster, static_model_publisher** 实时在RViz上标注目标点位与模型
4. **robot_commander.py** 监听/target_pose，TCP（60000端口）发送精确指令给机器人
5. **external_control.script** 在机器人侧直接执行“movel”、“movej”等动作完成点位移动

---

## 7. 文件说明补充

- **模型&配置**全部拆解详见 `/src/eli_cs_robot_description/config/cs625/` 下YAML文件和Xacro宏参数（见V3文档“文件树”章节）
- **参数、硬件插件、启动/功能说明**：详见各package内`README.md`和launch脚本。

---

## 8. 项目特点与技术总结

- **双控制架构**：为同一套机器人提供了工业现场与科研/教学等复合型需求的全覆盖。
- **解耦性与可移植性**：采用严格的ros2 topic/service/action标准，便于未来升级和维护。
- **软硬件协同优化**：直接桥接视觉/PLC/外部系统数据，实现极低延迟、高扩展性应用场景。
- **架构图与流程梳理**：详尽的Mermaid数据流、文件树与端到端链路解析，便于团队理解与二次开发。
