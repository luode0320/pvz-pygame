"""
配置加载器 - CrossVerse Arena核心模块
负责加载和验证所有YAML配置文件，支持热加载和自动扫描
"""

import os
import yaml
import logging
import time
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    配置加载器类
    功能：
    1. 自动扫描游戏IP、战役、性能配置目录
    2. 支持热加载，无需重启即可添加新内容
    3. 配置校验：必须字段、路径合法性、依赖关系、数值范围
    4. 错误处理：缺失字段、资源缺失、格式错误
    """

    def __init__(self, root_dir: str = "."):
        """
        初始化配置加载器

        参数:
            root_dir: 项目根目录路径
        """
        self.root_dir = Path(root_dir).resolve()

        # 配置目录路径
        self.games_dir = self.root_dir / "games"
        self.campaigns_dir = self.root_dir / "campaigns"
        self.performance_dir = self.root_dir / "performance"
        self.settings_file = self.root_dir / "settings.yaml"

        # 配置缓存
        self.games: Dict[str, Dict] = {}  # 游戏IP配置
        self.characters: Dict[str, Dict] = {}  # 角色配置
        self.bosses: Dict[str, Dict] = {}  # Boss配置
        self.skins: Dict[str, Dict] = {}  # 皮肤配置
        self.skills: Dict[str, Dict] = {}  # 技能配置
        self.effects: Dict[str, Dict] = {}  # 效果配置
        self.campaigns: Dict[str, Dict] = {}  # 战役配置
        self.levels: Dict[str, Dict] = {}  # 关卡配置
        self.performance_profiles: Dict[str, Dict] = {}  # 性能配置
        self.settings: Dict = {}  # 全局设置

        # 文件修改时间缓存（用于检测变更）
        self.file_timestamps: Dict[str, float] = {}

        # 热加载控制
        self.auto_scan_enabled = True
        self.scan_interval = 30  # 扫描间隔（秒）
        self.scan_thread: Optional[threading.Thread] = None

        logger.info(f"配置加载器初始化完成，根目录: {self.root_dir}")

    def load_yaml(self, file_path: Path) -> Optional[Dict]:
        """
        加载YAML文件

        参数:
            file_path: YAML文件路径

        返回:
            解析后的配置字典，失败返回None
        """
        try:
            if not file_path.exists():
                logger.warning(f"配置文件不存在: {file_path}")
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # 记录文件修改时间
            self.file_timestamps[str(file_path)] = file_path.stat().st_mtime

            logger.debug(f"成功加载配置文件: {file_path}")
            return config

        except yaml.YAMLError as e:
            logger.error(f"YAML格式错误 {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"加载配置文件失败 {file_path}: {e}")
            return None

    def validate_required_fields(self, config: Dict, required_fields: List[str],
                                config_name: str) -> bool:
        """
        验证必须字段

        参数:
            config: 配置字典
            required_fields: 必须字段列表
            config_name: 配置名称（用于日志）

        返回:
            验证是否通过
        """
        missing_fields = []
        for field in required_fields:
            if field not in config:
                missing_fields.append(field)

        if missing_fields:
            logger.error(f"{config_name} 缺少必须字段: {', '.join(missing_fields)}")
            return False

        return True

    def validate_path(self, path_str: str, base_dir: Path) -> Optional[Path]:
        """
        验证并转换路径

        参数:
            path_str: 路径字符串（相对或绝对路径）
            base_dir: 基准目录

        返回:
            绝对路径，验证失败返回None
        """
        try:
            # 相对路径转绝对路径
            if not os.path.isabs(path_str):
                abs_path = (base_dir / path_str).resolve()
            else:
                abs_path = Path(path_str).resolve()

            return abs_path

        except Exception as e:
            logger.error(f"路径验证失败 {path_str}: {e}")
            return None

    def load_game_meta(self, game_id: str) -> bool:
        """
        加载游戏IP元信息

        参数:
            game_id: 游戏ID

        返回:
            加载是否成功
        """
        meta_file = self.games_dir / game_id / "meta.yaml"
        config = self.load_yaml(meta_file)

        if not config:
            return False

        # 验证必须字段
        required_fields = ["name", "type", "version"]
        if not self.validate_required_fields(config, required_fields, f"游戏{game_id}"):
            return False

        # 存储配置
        config['game_id'] = game_id
        config['meta_file'] = str(meta_file)
        self.games[game_id] = config

        logger.info(f"加载游戏IP: {config['name']} ({game_id})")
        return True

    def load_character(self, game_id: str, character_file: Path) -> bool:
        """
        加载角色配置

        参数:
            game_id: 所属游戏ID
            character_file: 角色配置文件路径

        返回:
            加载是否成功
        """
        config = self.load_yaml(character_file)

        if not config:
            return False

        # 验证必须字段
        required_fields = ["character_id", "name", "type", "cost", "stats"]
        if not self.validate_required_fields(config, required_fields,
                                            f"角色{character_file.stem}"):
            return False

        # 验证stats必须字段
        stats_required = ["hp", "attack", "attack_range", "attack_speed"]
        if not self.validate_required_fields(config['stats'], stats_required,
                                            f"角色{config['character_id']}的stats"):
            return False

        # 存储配置
        character_id = config['character_id']
        config['game_id'] = game_id
        config['config_file'] = str(character_file)
        self.characters[character_id] = config

        logger.info(f"加载角色: {config['name']} ({character_id})")
        return True

    def load_skin(self, game_id: str, skin_file: Path) -> bool:
        """
        加载皮肤配置

        参数:
            game_id: 所属游戏ID
            skin_file: 皮肤配置文件路径

        返回:
            加载是否成功
        """
        config = self.load_yaml(skin_file)

        if not config:
            return False

        # 验证必须字段
        required_fields = ["skin_id", "name", "character_id"]
        if not self.validate_required_fields(config, required_fields,
                                            f"皮肤{skin_file.stem}"):
            return False

        # 验证角色是否存在
        character_id = config['character_id']
        if character_id not in self.characters:
            logger.warning(f"皮肤{config['skin_id']}引用的角色{character_id}不存在")

        # 存储配置
        skin_id = config['skin_id']
        config['game_id'] = game_id
        config['config_file'] = str(skin_file)
        self.skins[skin_id] = config

        logger.info(f"加载皮肤: {config['name']} ({skin_id})")
        return True

    def load_boss(self, game_id: str, boss_file: Path) -> bool:
        """
        加载Boss配置

        参数:
            game_id: 所属游戏ID
            boss_file: Boss配置文件路径

        返回:
            加载是否成功
        """
        config = self.load_yaml(boss_file)

        if not config:
            return False

        # 验证必须字段
        required_fields = ["boss_id", "name", "type", "stats"]
        if not self.validate_required_fields(config, required_fields,
                                            f"Boss{boss_file.stem}"):
            return False

        # 验证stats必须字段
        stats_required = ["hp", "attack", "attack_range", "attack_speed"]
        if not self.validate_required_fields(config['stats'], stats_required,
                                            f"Boss{config['boss_id']}的stats"):
            return False

        # 存储配置
        boss_id = config['boss_id']
        config['game_id'] = game_id
        config['config_file'] = str(boss_file)
        self.bosses[boss_id] = config

        logger.info(f"加载Boss: {config['name']} ({boss_id})")
        return True

    def get_boss_config(self, boss_id: str) -> Optional[Dict]:
        """
        获取Boss配置

        参数:
            boss_id: Boss ID

        返回:
            Boss配置字典，不存在返回None
        """
        return self.bosses.get(boss_id)

    def load_campaign(self, campaign_id: str) -> bool:
        """
        加载战役配置

        参数:
            campaign_id: 战役ID

        返回:
            加载是否成功
        """
        campaign_file = self.campaigns_dir / campaign_id / "campaign.yaml"
        config = self.load_yaml(campaign_file)

        if not config:
            return False

        # 验证必须字段
        required_fields = ["campaign_id", "name", "defender_game", "attacker_game"]
        if not self.validate_required_fields(config, required_fields,
                                            f"战役{campaign_id}"):
            return False

        # 验证游戏IP是否存在
        if config['defender_game'] not in self.games:
            logger.warning(f"战役{campaign_id}的防守方游戏{config['defender_game']}不存在")
        if config['attacker_game'] not in self.games:
            logger.warning(f"战役{campaign_id}的攻击方游戏{config['attacker_game']}不存在")

        # 加载关卡
        levels_dir = self.campaigns_dir / campaign_id / "levels"
        if levels_dir.exists():
            for level_file in levels_dir.glob("*.yaml"):
                self.load_level(campaign_id, level_file)

        # 存储配置
        config['config_file'] = str(campaign_file)
        self.campaigns[campaign_id] = config

        logger.info(f"加载战役: {config['name']} ({campaign_id})")
        return True

    def load_level(self, campaign_id: str, level_file: Path) -> bool:
        """
        加载关卡配置

        参数:
            campaign_id: 所属战役ID
            level_file: 关卡配置文件路径

        返回:
            加载是否成功
        """
        config = self.load_yaml(level_file)

        if not config:
            return False

        # 验证必须字段
        required_fields = ["level_id", "name", "waves"]
        if not self.validate_required_fields(config, required_fields,
                                            f"关卡{level_file.stem}"):
            return False

        # 存储配置
        level_id = f"{campaign_id}/{config['level_id']}"
        config['campaign_id'] = campaign_id
        config['config_file'] = str(level_file)
        self.levels[level_id] = config

        logger.info(f"加载关卡: {config['name']} ({level_id})")
        return True

    def load_performance_profile(self, profile_file: Path) -> bool:
        """
        加载性能配置文件

        参数:
            profile_file: 性能配置文件路径

        返回:
            加载是否成功
        """
        config = self.load_yaml(profile_file)

        if not config:
            return False

        # 验证必须字段
        required_fields = ["profile_id", "name"]
        if not self.validate_required_fields(config, required_fields,
                                            f"性能配置{profile_file.stem}"):
            return False

        # 存储配置
        profile_id = config['profile_id']
        config['config_file'] = str(profile_file)
        self.performance_profiles[profile_id] = config

        logger.info(f"加载性能配置: {config['name']} ({profile_id})")
        return True

    def load_settings(self) -> bool:
        """
        加载全局设置

        返回:
            加载是否成功
        """
        config = self.load_yaml(self.settings_file)

        if config:
            self.settings = config
            logger.info("加载全局设置成功")
            return True
        else:
            logger.warning("全局设置文件不存在或格式错误，使用默认设置")
            self.settings = self.get_default_settings()
            return False

    def get_default_settings(self) -> Dict:
        """
        获取默认全局设置

        返回:
            默认设置字典
        """
        return {
            "language": "zh",
            "resolution": [1280, 720],
            "fps": 60,
            "fullscreen": False,
            "skin_system": {
                "enabled": True,
                "default_skin": "basic"
            },
            "effect_system": {
                "max_effects_per_entity": 10,
                "effect_duration_scale": 1.0
            },
            "render_system": {
                "render_pipeline": "forward",
                "anti_aliasing": "fxaa"
            },
            "performance_system": {
                "enabled": True,
                "fps_warning_threshold": 30,
                "auto_adjust": True
            }
        }

    def scan_all(self) -> None:
        """
        扫描所有配置目录，加载配置
        """
        logger.info("开始扫描配置目录...")
        start_time = time.time()

        # 清空所有配置字典（确保删除的配置不再显示）
        self.games = {}
        self.characters = {}
        self.bosses = {}
        self.skins = {}
        self.levels = {}
        self.campaigns = {}
        self.performance_configs = {}

        # 加载全局设置
        self.load_settings()

        # 扫描游戏IP
        if self.games_dir.exists():
            for game_dir in self.games_dir.iterdir():
                if game_dir.is_dir() and not game_dir.name.startswith('.'):
                    game_id = game_dir.name

                    # 加载游戏元信息
                    self.load_game_meta(game_id)

                    # 加载角色
                    characters_dir = game_dir / "characters"
                    if characters_dir.exists():
                        for char_file in characters_dir.glob("*.yaml"):
                            self.load_character(game_id, char_file)

                    # 加载皮肤
                    skins_dir = game_dir / "skins"
                    if skins_dir.exists():
                        for skin_file in skins_dir.glob("*.yaml"):
                            self.load_skin(game_id, skin_file)

                    # 加载Boss配置
                    bosses_dir = game_dir / "bosses"
                    if bosses_dir.exists():
                        for boss_file in bosses_dir.glob("*.yaml"):
                            self.load_boss(game_id, boss_file)

        # 扫描战役
        if self.campaigns_dir.exists():
            for campaign_dir in self.campaigns_dir.iterdir():
                if campaign_dir.is_dir() and not campaign_dir.name.startswith('.'):
                    campaign_id = campaign_dir.name
                    self.load_campaign(campaign_id)

        # 扫描性能配置
        if self.performance_dir.exists():
            profiles_dir = self.performance_dir / "device_profiles"
            if profiles_dir.exists():
                for profile_file in profiles_dir.glob("*.yaml"):
                    self.load_performance_profile(profile_file)

        elapsed = time.time() - start_time
        logger.info(f"配置扫描完成，耗时: {elapsed:.2f}秒")
        logger.info(f"统计: {len(self.games)}个游戏IP, {len(self.characters)}个角色, "
                   f"{len(self.bosses)}个Boss, {len(self.skins)}个皮肤, {len(self.campaigns)}个战役, "
                   f"{len(self.levels)}个关卡, {len(self.performance_profiles)}个性能配置")

    def check_updates(self) -> List[str]:
        """
        检查配置文件更新

        返回:
            已更新的文件路径列表
        """
        updated_files = []

        for file_path, old_mtime in self.file_timestamps.items():
            path = Path(file_path)
            if path.exists():
                new_mtime = path.stat().st_mtime
                if new_mtime > old_mtime:
                    updated_files.append(file_path)

        return updated_files

    def auto_scan_loop(self) -> None:
        """
        自动扫描循环（在后台线程运行）
        """
        logger.info(f"启动自动扫描线程，扫描间隔: {self.scan_interval}秒")

        while self.auto_scan_enabled:
            time.sleep(self.scan_interval)

            if not self.auto_scan_enabled:
                break

            # 检查更新
            updated_files = self.check_updates()
            if updated_files:
                logger.info(f"检测到{len(updated_files)}个文件更新，重新加载配置")
                self.scan_all()

    def start_auto_scan(self) -> None:
        """
        启动自动扫描
        """
        if self.scan_thread and self.scan_thread.is_alive():
            logger.warning("自动扫描已在运行")
            return

        self.auto_scan_enabled = True
        self.scan_thread = threading.Thread(target=self.auto_scan_loop, daemon=True)
        self.scan_thread.start()

    def stop_auto_scan(self) -> None:
        """
        停止自动扫描
        """
        logger.info("停止自动扫描")
        self.auto_scan_enabled = False
        if self.scan_thread:
            self.scan_thread.join(timeout=1)

    def get_character(self, character_id: str) -> Optional[Dict]:
        """
        获取角色配置

        参数:
            character_id: 角色ID

        返回:
            角色配置字典，不存在返回None
        """
        return self.characters.get(character_id)

    def get_skin(self, skin_id: str) -> Optional[Dict]:
        """
        获取皮肤配置

        参数:
            skin_id: 皮肤ID

        返回:
            皮肤配置字典，不存在返回None
        """
        return self.skins.get(skin_id)

    def get_campaign(self, campaign_id: str) -> Optional[Dict]:
        """
        获取战役配置

        参数:
            campaign_id: 战役ID

        返回:
            战役配置字典，不存在返回None
        """
        return self.campaigns.get(campaign_id)

    def get_level(self, campaign_id: str, level_id: str) -> Optional[Dict]:
        """
        获取关卡配置

        参数:
            campaign_id: 战役ID
            level_id: 关卡ID

        返回:
            关卡配置字典，不存在返回None
        """
        full_level_id = f"{campaign_id}/{level_id}"
        return self.levels.get(full_level_id)

    def get_performance_profile(self, profile_id: str) -> Optional[Dict]:
        """
        获取性能配置

        参数:
            profile_id: 性能配置ID

        返回:
            性能配置字典，不存在返回None
        """
        return self.performance_profiles.get(profile_id)


# 全局配置加载器实例（单例模式）
_config_loader_instance: Optional[ConfigLoader] = None


def get_config_loader(root_dir: str = ".") -> ConfigLoader:
    """
    获取配置加载器实例（单例）

    参数:
        root_dir: 项目根目录

    返回:
        ConfigLoader实例
    """
    global _config_loader_instance

    if _config_loader_instance is None:
        _config_loader_instance = ConfigLoader(root_dir)

    return _config_loader_instance
