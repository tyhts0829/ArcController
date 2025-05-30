"""
ArcController パッケージ

このパッケージは、Monome Arcデバイス用のMIDIコントローラーアプリケーションを提供します。
"""

# パッケージの主要な機能をインポートして公開
from arc.app import main, run

# パッケージのバージョン（必要に応じて）
__version__ = "1.0.0"

# 公開するAPIを明示的に定義
__all__ = ["main", "run"]
