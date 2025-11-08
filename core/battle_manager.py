"""
战斗管理器 - 负责游戏玩法核心逻辑
包括：卡片系统、网格系统、单位管理、波次控制、战斗逻辑
"""

import pygame
import logging
import time
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class Defender:
    """防守单位（玩家放置的角色）"""

    def __init__(self, character_config: dict, grid_x: int, grid_y: int):
        self.character_id = character_config.get('character_id', 'unknown')
        self.name = character_config.get('name', '未知角色')
        self.config = character_config

        # 网格位置
        self.grid_x = grid_x
        self.grid_y = grid_y

        # 属性
        stats = character_config.get('stats', {})
        self.max_hp = stats.get('hp', 100)
        self.hp = self.max_hp
        self.attack = stats.get('attack', 10)
        self.attack_range = stats.get('attack_range', 200)
        self.attack_speed = stats.get('attack_speed', 1.0)

        # 攻击计时
        self.attack_cooldown = 0
        self.attack_interval = 1.0 / self.attack_speed

        # 目标
        self.target: Optional['Enemy'] = None

        # 动画状态
        self.animation_state = "idle"
        self.animation_time = 0

    def get_screen_pos(self, grid_start_x: int, grid_start_y: int, cell_size: int) -> Tuple[int, int]:
        """获取屏幕坐标"""
        x = grid_start_x + self.grid_x * cell_size + cell_size // 2
        y = grid_start_y + self.grid_y * cell_size + cell_size // 2
        return x, y

    def update(self, delta_time: float, enemies: List['Enemy']):
        """更新防守单位"""
        # 更新攻击冷却
        if self.attack_cooldown > 0:
            self.attack_cooldown -= delta_time

        # 更新动画时间
        self.animation_time += delta_time

        # 查找目标
        if self.target is None or not self.target.is_alive():
            self.find_target(enemies)

        # 攻击目标
        if self.target and self.attack_cooldown <= 0:
            distance = abs(self.target.x - self.grid_x * 100)
            if distance <= self.attack_range:
                self.attack_target()
                self.attack_cooldown = self.attack_interval
                self.animation_state = "attack"
                self.animation_time = 0
            else:
                self.target = None
                self.animation_state = "idle"

        # 重置动画
        if self.animation_state == "attack" and self.animation_time > 0.5:
            self.animation_state = "idle"

    def find_target(self, enemies: List['Enemy']):
        """查找攻击目标（最近的敌人）"""
        closest = None
        closest_distance = float('inf')

        for enemy in enemies:
            if enemy.is_alive() and enemy.lane == self.grid_y:
                distance = abs(enemy.x - self.grid_x * 100)
                if distance < closest_distance and distance <= self.attack_range:
                    closest = enemy
                    closest_distance = distance

        self.target = closest

    def attack_target(self):
        """攻击目标"""
        if self.target and self.target.is_alive():
            self.target.take_damage(self.attack)
            logger.debug(f"{self.name} 攻击 {self.target.name}，造成 {self.attack} 伤害")

    def take_damage(self, damage: int):
        """受到伤害"""
        self.hp -= damage
        if self.hp < 0:
            self.hp = 0

    def is_alive(self) -> bool:
        return self.hp > 0

    def render(self, screen: pygame.Surface, font, grid_start_x: int, grid_start_y: int, cell_size: int):
        """渲染防守单位"""
        x, y = self.get_screen_pos(grid_start_x, grid_start_y, cell_size)

        # 绘制角色圆形（简化版）
        if self.animation_state == "attack":
            color = (255, 200, 100)  # 攻击时黄色
        else:
            color = (100, 200, 255)  # 空闲时蓝色

        pygame.draw.circle(screen, color, (x, y), cell_size // 3)
        pygame.draw.circle(screen, (255, 255, 255), (x, y), cell_size // 3, 2)

        # 绘制名字
        name_text = font.render(self.name[:2], True, (255, 255, 255))
        name_rect = name_text.get_rect(center=(x, y))
        screen.blit(name_text, name_rect)

        # 绘制血条
        bar_width = cell_size
        bar_height = 5
        bar_x = x - bar_width // 2
        bar_y = y - cell_size // 2 - 10

        # 血条背景
        pygame.draw.rect(screen, (100, 0, 0), (bar_x, bar_y, bar_width, bar_height))
        # 血条前景
        hp_ratio = self.hp / self.max_hp
        pygame.draw.rect(screen, (0, 255, 0), (bar_x, bar_y, int(bar_width * hp_ratio), bar_height))


class Enemy:
    """敌人单位"""

    def __init__(self, character_config: dict, lane: int, screen_width: int, health_multiplier: float = 1.0):
        self.character_id = character_config.get('character_id', 'unknown')
        self.name = character_config.get('name', '未知敌人')
        self.config = character_config

        # 位置（从右边进入）
        self.lane = lane
        self.x = screen_width + 50  # 从屏幕右侧开始

        # 属性
        stats = character_config.get('stats', {})
        self.max_hp = int(stats.get('hp', 100) * health_multiplier)
        self.hp = self.max_hp
        self.attack = stats.get('attack', 10)
        self.speed = stats.get('speed', 20)  # 移动速度
        if self.speed == 0:  # 如果配置为0，设置默认速度
            self.speed = 20

        # 攻击计时
        self.attack_cooldown = 0
        self.attack_interval = 2.0

        # 状态
        self.blocked_by: Optional[Defender] = None

    def update(self, delta_time: float, defenders: List[Defender], grid_start_x: int, cell_size: int):
        """更新敌人"""
        # 更新攻击冷却
        if self.attack_cooldown > 0:
            self.attack_cooldown -= delta_time

        # 检查是否被阻挡
        self.blocked_by = None
        for defender in defenders:
            if defender.grid_y == self.lane and defender.is_alive():
                defender_x = grid_start_x + defender.grid_x * cell_size + cell_size // 2
                if abs(self.x - defender_x) < 50:
                    self.blocked_by = defender
                    break

        # 如果被阻挡，攻击防守单位
        if self.blocked_by:
            if self.attack_cooldown <= 0:
                self.blocked_by.take_damage(self.attack)
                self.attack_cooldown = self.attack_interval
                logger.debug(f"{self.name} 攻击 {self.blocked_by.name}，造成 {self.attack} 伤害")
        else:
            # 继续前进
            self.x -= self.speed * delta_time

    def take_damage(self, damage: int):
        """受到伤害"""
        self.hp -= damage
        if self.hp < 0:
            self.hp = 0

    def is_alive(self) -> bool:
        return self.hp > 0

    def reached_base(self, base_x: int) -> bool:
        """是否到达基地"""
        return self.x <= base_x

    def get_screen_pos(self, grid_start_y: int, cell_size: int) -> Tuple[int, int]:
        """获取屏幕坐标"""
        y = grid_start_y + self.lane * cell_size + cell_size // 2
        return int(self.x), y

    def render(self, screen: pygame.Surface, font, grid_start_y: int, cell_size: int):
        """渲染敌人"""
        x, y = self.get_screen_pos(grid_start_y, cell_size)

        # 绘制敌人方形（简化版）
        size = cell_size // 3
        color = (255, 100, 100)  # 红色

        rect = pygame.Rect(x - size, y - size, size * 2, size * 2)
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, (255, 255, 255), rect, 2)

        # 绘制名字
        name_text = font.render(self.name[:2], True, (255, 255, 255))
        name_rect = name_text.get_rect(center=(x, y))
        screen.blit(name_text, name_rect)

        # 绘制血条
        bar_width = size * 2
        bar_height = 5
        bar_x = x - bar_width // 2
        bar_y = y - size - 10

        # 血条背景
        pygame.draw.rect(screen, (100, 0, 0), (bar_x, bar_y, bar_width, bar_height))
        # 血条前景
        hp_ratio = self.hp / self.max_hp
        pygame.draw.rect(screen, (0, 255, 0), (bar_x, bar_y, int(bar_width * hp_ratio), bar_height))


class BattleManager:
    """
    战斗管理器
    管理整个战斗流程：卡片、网格、单位、波次、资源
    """

    def __init__(self, config_loader, level_config: dict):
        self.config_loader = config_loader
        self.level_config = level_config

        # 战场网格配置
        self.grid_rows = 5  # 5行
        self.grid_cols = 9  # 9列
        self.cell_size = 80
        self.grid_start_x = 100
        self.grid_start_y = 150  # 从150开始，为顶部卡片栏留出空间

        # 基地位置
        self.base_x = self.grid_start_x
        self.base_hp = 1000
        self.base_max_hp = 1000

        # 资源
        self.gold = 200  # 初始金币
        self.gold_generation_rate = 25  # 每秒生成金币
        self.gold_timer = 0

        # 卡片槽（可用角色）
        self.card_slots: List[dict] = []
        self.selected_card_index: Optional[int] = None

        # 网格占用情况
        self.grid: List[List[Optional[Defender]]] = [[None for _ in range(self.grid_cols)] for _ in range(self.grid_rows)]

        # 单位列表
        self.defenders: List[Defender] = []
        self.enemies: List[Enemy] = []

        # 波次管理
        self.waves = level_config.get('waves', [])
        self.current_wave_index = 0
        self.battle_time = 0
        self.all_waves_spawned = False

        # 游戏状态
        self.game_over = False
        self.victory = False

        # 玩家选择的角色列表（将由main.py设置）
        self.selected_characters: List[str] = []

        # 注意：不在这里初始化卡片槽，等待设置selected_characters后再初始化

        logger.info("战斗管理器初始化完成")

    def _init_card_slots(self):
        """初始化卡片槽（使用玩家选择的角色）"""
        if not self.selected_characters:
            logger.warning("未选择任何角色，加载所有防守方角色")
            # 如果没有选择角色，加载所有防守方角色
            for char_id, char_config in self.config_loader.characters.items():
                if char_config.get('type') == 'defender':
                    self.selected_characters.append(char_id)

        # 根据选择的角色创建卡片槽
        for char_id in self.selected_characters:
            char_config = self.config_loader.characters.get(char_id)
            if char_config:
                self.card_slots.append({
                    'character_id': char_id,
                    'name': char_config.get('name', char_id),
                    'cost': char_config.get('cost', 100),
                    'config': char_config,
                    'cooldown': 0,
                    'cooldown_max': 5.0  # 5秒冷却
                })

        logger.info(f"加载了 {len(self.card_slots)} 个角色卡片")

    def update(self, delta_time: float, screen_width: int):
        """更新战斗状态"""
        if self.game_over:
            return

        self.battle_time += delta_time

        # 更新资源生成
        self.gold_timer += delta_time
        if self.gold_timer >= 1.0:
            self.gold += self.gold_generation_rate
            self.gold_timer = 0

        # 更新卡片冷却
        for card in self.card_slots:
            if card['cooldown'] > 0:
                card['cooldown'] -= delta_time

        # 生成波次
        self._spawn_waves(screen_width)

        # 更新防守单位
        for defender in self.defenders[:]:
            defender.update(delta_time, self.enemies)
            if not defender.is_alive():
                self.defenders.remove(defender)
                self.grid[defender.grid_y][defender.grid_x] = None

        # 更新敌人
        for enemy in self.enemies[:]:
            enemy.update(delta_time, self.defenders, self.grid_start_x, self.cell_size)

            # 检查是否死亡
            if not enemy.is_alive():
                self.enemies.remove(enemy)
                self.gold += 25  # 击杀奖励

            # 检查是否到达基地
            elif enemy.reached_base(self.base_x):
                self.base_hp -= enemy.attack * 10
                self.enemies.remove(enemy)
                logger.info(f"敌人突破！基地受到 {enemy.attack * 10} 伤害")

        # 检查胜利/失败
        self._check_game_over()

    def _spawn_waves(self, screen_width: int):
        """生成敌人波次"""
        if self.all_waves_spawned:
            return

        for i, wave in enumerate(self.waves[self.current_wave_index:], self.current_wave_index):
            wave_time = wave.get('time', 0)

            if self.battle_time >= wave_time:
                # 生成这一波敌人
                enemies_config = wave.get('enemies', [])
                for enemy_group in enemies_config:
                    char_id = enemy_group.get('character')
                    count = enemy_group.get('count', 1)
                    health_mult = enemy_group.get('health_multiplier', 1.0)

                    # 获取角色配置
                    char_config = self.config_loader.characters.get(char_id)
                    if char_config:
                        for j in range(count):
                            lane = j % self.grid_rows  # 随机分配行
                            enemy = Enemy(char_config, lane, screen_width, health_mult)
                            self.enemies.append(enemy)

                logger.info(f"生成波次 {i + 1}")
                self.current_wave_index = i + 1

                if self.current_wave_index >= len(self.waves):
                    self.all_waves_spawned = True
                    break

    def _check_game_over(self):
        """检查游戏结束条件"""
        # 失败：基地血量为0
        if self.base_hp <= 0:
            self.game_over = True
            self.victory = False
            logger.info("游戏失败：基地被摧毁")

        # 胜利：所有波次生成且所有敌人被消灭
        if self.all_waves_spawned and len(self.enemies) == 0:
            self.game_over = True
            self.victory = True
            logger.info("游戏胜利：击退所有敌人")

    def place_defender(self, grid_x: int, grid_y: int) -> bool:
        """放置防守单位"""
        # 检查是否选择了卡片
        if self.selected_card_index is None:
            return False

        card = self.card_slots[self.selected_card_index]

        # 检查金币是否足够
        if self.gold < card['cost']:
            logger.debug("金币不足")
            return False

        # 检查冷却
        if card['cooldown'] > 0:
            logger.debug("卡片冷却中")
            return False

        # 检查网格是否可用
        if grid_x < 0 or grid_x >= self.grid_cols or grid_y < 0 or grid_y >= self.grid_rows:
            return False

        if self.grid[grid_y][grid_x] is not None:
            logger.debug("该位置已有单位")
            return False

        # 创建防守单位
        defender = Defender(card['config'], grid_x, grid_y)
        self.defenders.append(defender)
        self.grid[grid_y][grid_x] = defender

        # 扣除金币，设置冷却
        self.gold -= card['cost']
        card['cooldown'] = card['cooldown_max']

        logger.info(f"放置 {defender.name} 在 ({grid_x}, {grid_y})")
        return True

    def render(self, screen: pygame.Surface, fonts: dict):
        """渲染战斗界面"""
        # 绘制网格
        self._render_grid(screen)

        # 绘制防守单位
        for defender in self.defenders:
            defender.render(screen, fonts['small'], self.grid_start_x, self.grid_start_y, self.cell_size)

        # 绘制敌人
        for enemy in self.enemies:
            enemy.render(screen, fonts['small'], self.grid_start_y, self.cell_size)

        # 绘制卡片槽
        self._render_card_slots(screen, fonts)

        # 绘制UI信息
        self._render_ui(screen, fonts)

    def _render_grid(self, screen: pygame.Surface):
        """渲染网格"""
        for row in range(self.grid_rows):
            for col in range(self.grid_cols):
                x = self.grid_start_x + col * self.cell_size
                y = self.grid_start_y + row * self.cell_size

                # 绘制网格线
                color = (60, 80, 60) if (row + col) % 2 == 0 else (50, 70, 50)
                pygame.draw.rect(screen, color, (x, y, self.cell_size, self.cell_size))
                pygame.draw.rect(screen, (80, 100, 80), (x, y, self.cell_size, self.cell_size), 1)

    def _render_card_slots(self, screen: pygame.Surface, fonts: dict):
        """渲染卡片槽（参考植物大战僵尸，在顶部显示）"""
        card_width = 80
        card_height = 100
        card_spacing = 10
        start_x = 250  # 从左边留出空间显示资源信息
        start_y = 20  # 顶部20像素开始

        for i, card in enumerate(self.card_slots):
            x = start_x + i * (card_width + card_spacing)
            y = start_y

            # 判断是否可用
            can_afford = self.gold >= card['cost']
            is_ready = card['cooldown'] <= 0
            is_selected = i == self.selected_card_index

            # 绘制卡片背景
            if is_selected:
                color = (100, 150, 255)
            elif can_afford and is_ready:
                color = (80, 120, 80)
            else:
                color = (60, 60, 60)

            pygame.draw.rect(screen, color, (x, y, card_width, card_height))
            pygame.draw.rect(screen, (200, 200, 200), (x, y, card_width, card_height), 2)

            # 绘制角色名
            name_text = fonts['small'].render(card['name'][:4], True, (255, 255, 255))
            name_rect = name_text.get_rect(center=(x + card_width // 2, y + 30))
            screen.blit(name_text, name_rect)

            # 绘制费用
            cost_text = fonts['small'].render(f"{card['cost']}", True, (255, 200, 50))
            cost_rect = cost_text.get_rect(center=(x + card_width // 2, y + 60))
            screen.blit(cost_text, cost_rect)

            # 绘制冷却
            if card['cooldown'] > 0:
                cooldown_text = fonts['small'].render(f"{card['cooldown']:.1f}s", True, (255, 100, 100))
                cooldown_rect = cooldown_text.get_rect(center=(x + card_width // 2, y + 85))
                screen.blit(cooldown_text, cooldown_rect)

    def _render_ui(self, screen: pygame.Surface, fonts: dict):
        """渲染UI信息"""
        # 基地血量
        hp_text = fonts['normal'].render(f"基地 HP: {max(0, self.base_hp)} / {self.base_max_hp}", True, (255, 100, 100))
        screen.blit(hp_text, (20, 20))

        # 金币
        gold_text = fonts['normal'].render(f"金币: {self.gold}", True, (255, 200, 50))
        screen.blit(gold_text, (20, 60))

        # 波次信息
        wave_text = fonts['small'].render(
            f"波次: {self.current_wave_index}/{len(self.waves)} | 敌人: {len(self.enemies)}",
            True,
            (200, 200, 200)
        )
        screen.blit(wave_text, (screen.get_width() - 300, 60))

    def handle_click(self, mouse_x: int, mouse_y: int, screen_height: int):
        """处理鼠标点击"""
        # 检查是否点击卡片槽（顶部位置）
        card_width = 80
        card_height = 100
        card_spacing = 10
        start_x = 250  # 与渲染保持一致
        start_y = 20  # 与渲染保持一致

        for i, card in enumerate(self.card_slots):
            x = start_x + i * (card_width + card_spacing)
            y = start_y

            if x <= mouse_x <= x + card_width and y <= mouse_y <= y + card_height:
                # 检查是否可选
                if self.gold >= card['cost'] and card['cooldown'] <= 0:
                    self.selected_card_index = i if self.selected_card_index != i else None
                    logger.debug(f"选择卡片: {card['name']}")
                return

        # 检查是否点击网格
        if self.selected_card_index is not None:
            grid_x = (mouse_x - self.grid_start_x) // self.cell_size
            grid_y = (mouse_y - self.grid_start_y) // self.cell_size

            if 0 <= grid_x < self.grid_cols and 0 <= grid_y < self.grid_rows:
                if self.place_defender(grid_x, grid_y):
                    self.selected_card_index = None  # 放置后取消选择
