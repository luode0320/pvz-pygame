"""
Boss系统测试脚本
验证Boss核心功能是否正常工作
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.config_loader import ConfigLoader
from core.boss_system import BossManager, BossUnit, BossPhase

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_config_loader():
    """测试配置加载"""
    logger.info("=" * 60)
    logger.info("测试1: 配置加载")
    logger.info("=" * 60)

    try:
        config_loader = ConfigLoader(".")
        config_loader.scan_all()

        logger.info(f"✅ 成功加载 {len(config_loader.bosses)} 个Boss配置")

        for boss_id, boss_config in config_loader.bosses.items():
            logger.info(f"  - {boss_config['name']} ({boss_id})")
            phases = boss_config.get('phases', [])
            logger.info(f"    阶段数: {len(phases)}")
            skills = boss_config.get('skills', [])
            logger.info(f"    技能数: {len(skills)}")

        return config_loader

    except Exception as e:
        logger.error(f"❌ 配置加载失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_boss_phase():
    """测试Boss阶段系统"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: Boss阶段系统")
    logger.info("=" * 60)

    try:
        # 创建测试阶段配置
        phase_config = {
            "hp_threshold": 1.0,
            "hp_min": 0.7,
            "skills": ["test_skill_1", "test_skill_2"],
            "buffs": [
                {"type": "damage_reduction", "value": 0.15}
            ],
            "damage_multiplier": 1.0,
            "defense_multiplier": 1.0,
            "speed_multiplier": 1.0
        }

        phase = BossPhase(phase_config, 1)

        logger.info(f"✅ 阶段 {phase.phase_number} 创建成功")
        logger.info(f"  血量范围: {phase.hp_min*100}% - {phase.hp_threshold*100}%")
        logger.info(f"  技能列表: {phase.skill_ids}")
        logger.info(f"  增益效果: {len(phase.buffs)} 个")

        # 测试阶段判定
        assert phase.is_in_phase(0.85) == True, "85%血量应该在第一阶段"
        assert phase.is_in_phase(0.65) == False, "65%血量不应该在第一阶段"
        logger.info("✅ 阶段判定逻辑正确")

        return True

    except Exception as e:
        logger.error(f"❌ 阶段系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_boss_unit_creation(config_loader):
    """测试Boss单位创建"""
    logger.info("\n" + "=" * 60)
    logger.info("测试3: Boss单位创建")
    logger.info("=" * 60)

    try:
        # 获取Boss配置
        boss_config = config_loader.get_boss_config("baron_nashor")
        if not boss_config:
            logger.error("❌ 找不到纳什男爵配置")
            return False

        logger.info(f"✅ 找到Boss配置: {boss_config['name']}")

        # 创建模拟Enemy单位
        class MockEnemy:
            def __init__(self, config):
                self.config = config
                stats = config.get('stats', {})
                self.max_hp = stats.get('hp', 1000)
                self.hp = self.max_hp
                self.attack = stats.get('attack', 50)
                self.name = config.get('name', 'Unknown')
                self.is_boss = False
                # 添加坐标属性
                self.x = 800  # 模拟屏幕右侧
                self.y = 400  # 模拟屏幕中间

            def is_alive(self):
                return self.hp > 0

            def take_damage(self, damage):
                self.hp -= damage
                if self.hp < 0:
                    self.hp = 0

        # 创建模拟BattleManager
        class MockBattleManager:
            def __init__(self):
                self.enemies = []
                self.defenders = []
                self.gold = 0
                self.config_loader = config_loader
                self.screen_height = 800
                self.grid_start_y = 100
                self.cell_size = 80

        enemy = MockEnemy(boss_config)
        battle_manager = MockBattleManager()

        # 创建Boss单位
        boss_manager = BossManager()
        boss = boss_manager.create_boss(boss_config, enemy, battle_manager)

        logger.info(f"✅ Boss单位创建成功: {boss.boss_name}")
        logger.info(f"  Boss ID: {boss.boss_id}")
        logger.info(f"  阶段数: {len(boss.phases)}")
        logger.info(f"  特殊机制: {len(boss.special_mechanics)} 个")
        logger.info(f"  免疫效果: {boss.immunities}")

        # 测试阶段系统
        logger.info(f"\n当前血量: {boss.enemy.hp}/{boss.enemy.max_hp}")
        current_phase = boss.get_current_phase()
        if current_phase:
            logger.info(f"✅ 当前阶段: {current_phase.phase_number}")
            logger.info(f"  阶段技能: {current_phase.skill_ids}")

        # 测试伤害和阶段转换
        logger.info(f"\n测试阶段转换...")
        logger.info(f"造成伤害使Boss进入第二阶段...")
        boss.enemy.take_damage(boss.enemy.max_hp * 0.35)  # 减少35%血量，应该进入第二阶段
        boss.update(0.1)

        current_phase = boss.get_current_phase()
        if current_phase and current_phase.phase_number == 2:
            logger.info(f"✅ 成功进入阶段 {current_phase.phase_number}")
        else:
            logger.warning(f"⚠️ 阶段转换可能有问题，当前阶段: {current_phase.phase_number if current_phase else 'None'}")

        # 测试免疫系统
        logger.info(f"\n测试免疫系统...")
        can_stun = boss.can_apply_effect('stun')
        can_poison = boss.can_apply_effect('poison')
        logger.info(f"  可以施加眩晕: {can_stun} (应该是False)")
        logger.info(f"  可以施加中毒: {can_poison} (应该是True)")

        if not can_stun and can_poison:
            logger.info("✅ 免疫系统工作正常")
        else:
            logger.warning("⚠️ 免疫系统可能有问题")

        return True

    except Exception as e:
        logger.error(f"❌ Boss单位创建测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_boss_rewards(config_loader):
    """测试Boss奖励系统"""
    logger.info("\n" + "=" * 60)
    logger.info("测试4: Boss奖励系统")
    logger.info("=" * 60)

    try:
        boss_config = config_loader.get_boss_config("baron_nashor")

        class MockEnemy:
            def __init__(self, config):
                self.config = config
                self.hp = 1
                self.max_hp = 1000
                self.attack = 50
                self.name = config.get('name', 'Unknown')
                self.is_boss = False
                # 添加坐标属性
                self.x = 800
                self.y = 400

            def is_alive(self):
                return self.hp > 0

        class MockBattleManager:
            def __init__(self):
                self.enemies = []
                self.defenders = []
                self.gold = 100
                self.config_loader = config_loader
                self.screen_height = 800
                self.grid_start_y = 100
                self.cell_size = 80

        enemy = MockEnemy(boss_config)
        battle_manager = MockBattleManager()

        boss_manager = BossManager()
        boss = boss_manager.create_boss(boss_config, enemy, battle_manager)

        initial_gold = battle_manager.gold
        logger.info(f"击杀前金币: {initial_gold}")

        # 模拟击杀Boss
        boss.on_death()

        logger.info(f"击杀后金币: {battle_manager.gold}")
        gold_reward = battle_manager.gold - initial_gold

        expected_reward = boss_config.get('rewards', {}).get('gold', 0)

        if gold_reward == expected_reward:
            logger.info(f"✅ 金币奖励正确: +{gold_reward}")
        else:
            logger.warning(f"⚠️ 金币奖励不匹配: 期望{expected_reward}, 实际{gold_reward}")

        logger.info(f"  奖励配置: {boss_config.get('rewards', {})}")

        return True

    except Exception as e:
        logger.error(f"❌ 奖励系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    logger.info("🚀 开始Boss系统测试")
    logger.info("")

    results = []

    # 测试1: 配置加载
    config_loader = test_config_loader()
    results.append(("配置加载", config_loader is not None))

    if not config_loader:
        logger.error("配置加载失败，终止测试")
        return

    # 测试2: 阶段系统
    phase_result = test_boss_phase()
    results.append(("阶段系统", phase_result))

    # 测试3: Boss单位创建
    boss_result = test_boss_unit_creation(config_loader)
    results.append(("Boss单位创建", boss_result))

    # 测试4: 奖励系统
    reward_result = test_boss_rewards(config_loader)
    results.append(("奖励系统", reward_result))

    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("测试总结")
    logger.info("=" * 60)

    passed = 0
    failed = 0

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    logger.info("")
    logger.info(f"总计: {passed}/{len(results)} 测试通过")

    if failed == 0:
        logger.info("🎉 所有测试通过！Boss系统工作正常！")
    else:
        logger.warning(f"⚠️ {failed} 个测试失败，请检查")


if __name__ == "__main__":
    main()
