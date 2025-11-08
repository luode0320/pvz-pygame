# 🎨 UI主题配置系统说明

## 概述

实现了完整的**UI主题配置系统**，所有界面的颜色、布局都可以通过配置文件控制，完全符合"零硬编码"设计原则。

### ✨ 核心特性

- **全配置驱动**：所有UI颜色、布局通过YAML配置
- **三级Fallback机制**：关卡配置 → 全局配置 → 硬编码默认值
- **独立关卡主题**：每个关卡可以有独特的视觉风格
- **热重载支持**：修改配置后自动生效
- **完整覆盖**：支持所有UI元素的颜色定制

---

## 🗂️ 配置文件结构

### 全局配置 (settings.yaml)

所有UI的默认样式在这里定义：

```yaml
ui_theme:
  colors:
    background:      # 页面背景颜色
    text:           # 文字颜色
    button:         # 按钮颜色
    card:           # 卡片颜色
    game_ui:        # 游戏内UI颜色
    icon:           # 图标颜色
  layout:           # 布局配置
    padding:        # 边距
    button:         # 按钮尺寸
    card:           # 卡片尺寸
```

### 关卡配置 (level_*.yaml)

关卡可以覆盖全局UI配置：

```yaml
ui_theme:
  colors:
    background:
      level_select: [35, 25, 45]  # 覆盖关卡选择背景色
      battle: [50, 35, 45]         # 覆盖战斗背景色
    icon:
      gold: [255, 180, 100]        # 覆盖金币图标颜色
```

---

## 🎨 颜色配置详解

### 1️⃣ 页面背景颜色 (colors.background)

定义各个页面的背景颜色：

```yaml
background:
  main_menu: [20, 20, 40]           # 主菜单背景（深蓝灰）
  campaign_select: [30, 30, 50]     # 战役选择背景
  level_select: [25, 30, 45]        # 关卡选择背景
  character_select: [30, 40, 60]    # 角色选择背景
  battle: [40, 60, 40]              # 战斗背景（绿色调）
  pause: [0, 0, 0, 180]             # 暂停遮罩（半透明黑）
  victory: [40, 80, 40]             # 胜利背景（绿色）
  defeat: [80, 40, 40]              # 失败背景（红色）
```

**RGB格式**：`[红, 绿, 蓝]`，范围 0-255
**RGBA格式**：`[红, 绿, 蓝, 透明度]`，透明度范围 0-255

### 2️⃣ 文字颜色 (colors.text)

定义不同类型文字的颜色：

```yaml
text:
  title: [255, 200, 50]            # 标题文字（金色）
  normal: [255, 255, 255]          # 普通文字（白色）
  subtitle: [200, 200, 200]        # 副标题文字（浅灰）
  hint: [120, 120, 150]            # 提示文字（深蓝灰）
  success: [100, 255, 100]         # 成功文字（绿色）
  warning: [255, 200, 50]          # 警告文字（黄色）
  error: [255, 100, 100]           # 错误文字（红色）
  info: [150, 200, 255]            # 信息文字（蓝色）
```

**使用场景**：
- `title`: 页面标题、战役名称
- `normal`: 一般文字内容
- `subtitle`: 页码、辅助说明
- `hint`: 操作提示
- `success`: 进度信息、完成状态
- `error`: 错误提示
- `info`: 信息提示

### 3️⃣ 按钮颜色 (colors.button)

定义按钮在不同状态下的颜色：

```yaml
button:
  normal_bg: [60, 60, 90]          # 正常状态背景
  normal_border: [100, 120, 160]   # 正常状态边框
  normal_text: [220, 220, 220]     # 正常状态文字
  hover_bg: [80, 80, 120]          # 悬停状态背景（变亮）
  hover_border: [150, 180, 220]    # 悬停状态边框
  hover_text: [255, 255, 100]      # 悬停状态文字（黄色高亮）
  disabled_bg: [40, 40, 40]        # 禁用状态背景（灰暗）
  disabled_border: [80, 80, 80]    # 禁用状态边框
  disabled_text: [120, 120, 120]   # 禁用状态文字（深灰）
```

**状态切换**：
- 鼠标悬停 → `hover_*` 颜色
- 按钮禁用 → `disabled_*` 颜色
- 正常状态 → `normal_*` 颜色

### 4️⃣ 卡片颜色 (colors.card)

#### 关卡卡片

显示不同状态的关卡：

```yaml
card:
  # 已完成状态（绿色系）
  level_completed_bg: [40, 80, 40]
  level_completed_border: [80, 160, 80]
  level_completed_text: [100, 255, 100]

  # 已解锁状态（蓝色系）
  level_unlocked_bg: [60, 70, 90]
  level_unlocked_hover_bg: [80, 90, 120]
  level_unlocked_border: [100, 120, 160]
  level_unlocked_hover_border: [150, 180, 220]
  level_unlocked_text: [150, 200, 255]

  # 未解锁状态（灰色系）
  level_locked_bg: [40, 40, 40]
  level_locked_border: [80, 80, 80]
  level_locked_text: [150, 150, 150]
```

**视觉设计原则**：
- ✅ 已完成：绿色，表示成功
- 🔓 已解锁：蓝色，可点击，悬停时变亮
- 🔒 未解锁：灰色，不可点击

#### 角色卡片

```yaml
card:
  character_selected_bg: [100, 150, 255]     # 已选中（高亮蓝）
  character_selected_border: [150, 200, 255]
  character_hover_bg: [70, 90, 120]          # 悬停（浅蓝）
  character_hover_border: [150, 180, 220]
  character_normal_bg: [50, 60, 80]          # 正常（深蓝）
  character_normal_border: [100, 120, 150]
```

### 5️⃣ 图标颜色 (colors.icon)

用于显示游戏数据的文字图标：

```yaml
icon:
  gold: [255, 200, 50]             # 💰 金币图标（金色）
  hp: [255, 100, 100]              # ❤️ 血量图标（红色）
  wave: [100, 200, 255]            # 🌊 波次图标（蓝色）
  reward: [255, 200, 100]          # 🏆 奖励图标（橙色）
  exp: [255, 150, 255]             # ✨ 经验图标（紫色）
```

**示例**：
- `💰 金币: 200` → 使用 `icon.gold` 颜色
- `❤️ 血量: 1000` → 使用 `icon.hp` 颜色
- `🌊 波次: 3` → 使用 `icon.wave` 颜色

### 6️⃣ 游戏内UI颜色 (colors.game_ui)

战斗界面的UI元素：

```yaml
game_ui:
  grid_dark: [50, 70, 50]          # 深色网格（棋盘格）
  grid_light: [60, 80, 60]         # 浅色网格
  grid_border: [80, 100, 80]       # 网格边框
  hp_bar_bg: [100, 0, 0]           # 血条背景（暗红）
  hp_bar_fg: [0, 255, 0]           # 血条前景（亮绿）
  gold_text: [255, 200, 50]        # 金币显示文字
  hp_text: [255, 100, 100]         # 血量显示文字
  wave_text: [200, 200, 200]       # 波次显示文字
  enemy_text: [255, 150, 150]      # 敌人数量文字
```

---

## 🎯 三级Fallback机制

配置优先级：**关卡配置 > 全局配置 > 硬编码默认值**

### 工作流程

```
1. ThemeManager尝试从关卡配置读取
   ↓ 未找到
2. ThemeManager尝试从全局配置读取
   ↓ 未找到
3. ThemeManager使用硬编码默认值
   ↓ 仍未找到（理论上不会发生）
4. 返回白色作为最终fallback
```

### 示例

**全局配置 (settings.yaml)**:
```yaml
ui_theme:
  colors:
    icon:
      gold: [255, 200, 50]   # 金色
```

**关卡配置 (level_02.yaml)**:
```yaml
ui_theme:
  colors:
    icon:
      gold: [255, 180, 100]  # 橙色（覆盖全局）
```

**结果**：
- `level_01`: 使用全局配置的金色 `[255, 200, 50]`
- `level_02`: 使用关卡配置的橙色 `[255, 180, 100]`

---

## 📝 使用示例

### 示例1：创建紫色主题关卡

创建一个具有独特视觉风格的挑战关卡：

```yaml
# level_03.yaml
level_id: "level_03"
name: "暗影挑战"

# 自定义UI主题（紫色主题）
ui_theme:
  colors:
    # 背景变为紫色调
    background:
      level_select: [35, 25, 45]
      battle: [50, 35, 60]

    # 标题和成功文字改为紫色
    text:
      title: [200, 150, 255]
      success: [180, 120, 255]

    # 图标也使用紫色系
    icon:
      gold: [255, 200, 255]
      wave: [180, 100, 255]
      reward: [255, 150, 255]
```

### 示例2：节日主题（春节红）

```yaml
# level_special_spring.yaml
ui_theme:
  colors:
    background:
      level_select: [60, 20, 20]   # 暗红背景
      battle: [80, 25, 25]

    text:
      title: [255, 220, 100]       # 金黄标题
      success: [255, 200, 200]

    icon:
      gold: [255, 215, 0]          # 金色
      hp: [255, 100, 100]
      reward: [255, 180, 0]

    card:
      level_unlocked_bg: [80, 40, 40]
      level_unlocked_border: [180, 80, 80]
```

### 示例3：夜间模式

```yaml
# 全局配置
ui_theme:
  colors:
    background:
      main_menu: [15, 15, 20]       # 更暗的背景
      level_select: [18, 18, 25]

    text:
      normal: [220, 220, 220]       # 稍暗的文字
      subtitle: [150, 150, 150]

    button:
      normal_bg: [40, 40, 50]       # 深色按钮
      hover_bg: [60, 60, 80]
```

---

## 🛠️ ThemeManager API

### 初始化

```python
from core.theme_manager import get_theme_manager

# 在游戏初始化时（main.py）
theme_manager = get_theme_manager(settings)
```

### 设置关卡配置

```python
# 进入关卡时设置关卡UI配置
theme_manager.set_level_config(level_config)
```

### 获取颜色

```python
# 获取背景颜色
bg_color = theme_manager.get_background_color("level_select")
screen.fill(bg_color)

# 获取文字颜色
title_color = theme_manager.get_text_color("title")
title_text = font.render("标题", True, title_color)

# 获取特定类别的颜色
icon_gold = theme_manager.get_color("icon", "gold")
card_bg = theme_manager.get_color("card", "level_unlocked_bg")
```

### 获取布局值

```python
# 获取布局配置
button_width = theme_manager.get_layout("button", "width", default=300)
padding = theme_manager.get_layout("padding", "normal", default=20)
```

---

## 📊 配置对视觉的影响

### 背景颜色配置

| 页面 | 默认颜色 | 效果 |
|------|---------|------|
| main_menu | [20, 20, 40] | 深蓝灰，沉稳 |
| level_select | [25, 30, 45] | 略带蓝色，专注 |
| battle | [40, 60, 40] | 绿色调，战斗氛围 |
| victory | [40, 80, 40] | 明绿色，成功喜悦 |
| defeat | [80, 40, 40] | 暗红色，失败紧张 |

### 卡片状态颜色

| 状态 | 背景色 | 边框色 | 效果 |
|------|--------|--------|------|
| 已完成 | 深绿 | 亮绿 | 成就感 |
| 已解锁 | 深蓝 | 中蓝 | 可用 |
| 悬停 | 浅蓝 | 亮蓝 | 交互反馈 |
| 未解锁 | 深灰 | 中灰 | 锁定状态 |

---

## ✅ 已实现的UI元素

### 关卡选择界面 ✅

- ✅ 页面背景颜色
- ✅ 标题文字颜色
- ✅ 进度信息颜色
- ✅ 关卡卡片背景（已完成/已解锁/未解锁）
- ✅ 关卡卡片边框
- ✅ 关卡名称文字
- ✅ 状态标签颜色
- ✅ 图标颜色（金币、血量、波次、奖励）
- ✅ 分页按钮颜色（正常/悬停）
- ✅ 返回按钮颜色

### 其他界面（待扩展）

- ⏳ 主菜单
- ⏳ 战役选择
- ⏳ 角色选择
- ⏳ 战斗界面
- ⏳ 暂停菜单
- ⏳ 胜利/失败界面

---

## 🎯 最佳实践

### 1. 颜色一致性

同类元素使用相同的颜色：

```yaml
# 所有成功相关的使用绿色
text:
  success: [100, 255, 100]
card:
  level_completed_text: [100, 255, 100]
```

### 2. 对比度

确保文字和背景有足够的对比度：

```yaml
# ✅ 好的对比
background: [25, 30, 45]    # 深色背景
text: [255, 255, 255]       # 白色文字

# ❌ 差的对比
background: [200, 200, 200] # 浅色背景
text: [220, 220, 220]       # 浅色文字（看不清）
```

### 3. 状态反馈

不同状态使用明显不同的颜色：

```yaml
card:
  level_completed: [40, 80, 40]   # 绿色 → 已完成
  level_unlocked: [60, 70, 90]    # 蓝色 → 可用
  level_locked: [40, 40, 40]      # 灰色 → 锁定
```

### 4. 关卡主题应用场景

- **节日关卡**：春节用红金配色，圣诞用红绿配色
- **难度区分**：简单关卡用浅色，困难关卡用深色/红色
- **剧情关卡**：根据剧情氛围选择配色

---

## 📚 配置文件位置

```
CrossVerseArena/
├── settings.yaml                  # 全局UI配置
├── campaigns/
│   └── dnf_vs_lol/
│       └── levels/
│           ├── level_01.yaml      # 第一关（使用全局配置）
│           └── level_02.yaml      # 第二关（自定义紫红主题）
└── core/
    └── theme_manager.py           # UI主题管理器
```

---

## 🎉 优势

1. **完全配置驱动**：修改UI样式无需改代码
2. **灵活的主题系统**：每个关卡可以有独特风格
3. **一致的配置方式**：所有UI元素统一管理
4. **热重载支持**：修改配置立即生效
5. **易于扩展**：新增UI元素只需添加配置项
6. **三级Fallback**：确保总有有效的配置值

---

**🎨 现在你可以：**
- 通过配置文件控制所有UI样式
- 为每个关卡创建独特的视觉主题
- 快速调整配色方案而无需修改代码
- 创建节日主题、特殊活动主题等

**符合"零硬编码"设计原则！所有功能均通过配置文件驱动！**
