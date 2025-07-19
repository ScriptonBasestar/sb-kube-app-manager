import ast
import operator
import os
import re
from typing import Any


class ConditionEvaluator:
    """조건 평가기"""

    def __init__(self, context: dict[str, Any] = None):
        self.context = context or {}
        self.context.update(
            {"env": dict(os.environ), "true": True, "false": False, "null": None}
        )

    def evaluate(self, condition: str) -> bool:
        """조건 평가 - 안전한 AST 기반 평가"""
        if not condition or condition.strip() == "":
            return True

        try:
            # 안전한 평가를 위한 전처리
            safe_condition = self._preprocess_condition(condition)

            # AST를 사용한 안전한 평가
            return self._safe_eval(safe_condition)

        except Exception as e:
            # 조건 평가 실패 시 False 반환
            print(f"조건 평가 실패 '{condition}': {e}")
            return False

    def _safe_eval(self, expr: str) -> bool:
        """AST를 사용한 안전한 표현식 평가"""
        # 허용된 연산자들
        allowed_operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Mod: operator.mod,
            ast.Eq: operator.eq,
            ast.NotEq: operator.ne,
            ast.Lt: operator.lt,
            ast.LtE: operator.le,
            ast.Gt: operator.gt,
            ast.GtE: operator.ge,
            ast.And: operator.and_,
            ast.Or: operator.or_,
            ast.Not: operator.not_,
            ast.In: lambda x, y: x in y,
            ast.NotIn: lambda x, y: x not in y,
            ast.Is: operator.is_,
            ast.IsNot: operator.is_not,
        }

        # 허용된 이름들
        allowed_names = {
            "context": self.context,
            "env": self.context.get("env", {}),
            "cache": self.context.get("cache", {}),
            "true": True,
            "false": False,
            "null": None,
            "True": True,
            "False": False,
            "None": None,
        }

        def _eval_node(node):
            if isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.Name):
                if node.id in allowed_names:
                    return allowed_names[node.id]
                raise ValueError(f"이름 '{node.id}'는 허용되지 않습니다")
            elif isinstance(node, ast.BinOp):
                left = _eval_node(node.left)
                right = _eval_node(node.right)
                return allowed_operators[type(node.op)](left, right)
            elif isinstance(node, ast.UnaryOp):
                operand = _eval_node(node.operand)
                return allowed_operators[type(node.op)](operand)
            elif isinstance(node, ast.Compare):
                left = _eval_node(node.left)
                for op, comparator in zip(node.ops, node.comparators, strict=False):
                    right = _eval_node(comparator)
                    if not allowed_operators[type(op)](left, right):
                        return False
                    left = right
                return True
            elif isinstance(node, ast.BoolOp):
                values = [_eval_node(value) for value in node.values]
                if isinstance(node.op, ast.And):
                    return all(values)
                elif isinstance(node.op, ast.Or):
                    return any(values)
            elif isinstance(node, ast.Attribute):
                obj = _eval_node(node.value)
                return getattr(obj, node.attr)
            elif isinstance(node, ast.Subscript):
                obj = _eval_node(node.value)
                key = _eval_node(node.slice)
                return obj[key]
            elif isinstance(node, ast.Call):
                # 특정 안전한 함수만 허용
                if isinstance(node.func, ast.Attribute):
                    obj = _eval_node(node.func.value)
                    method = node.func.attr
                    args = [_eval_node(arg) for arg in node.args]

                    # dict.get 메소드 허용
                    if isinstance(obj, dict) and method == "get":
                        return obj.get(*args)
                    # Path.exists 메소드 허용
                    elif (
                        hasattr(obj, "__class__")
                        and obj.__class__.__name__ == "Path"
                        and method == "exists"
                    ):
                        return obj.exists()

                raise ValueError(f"함수 호출은 허용되지 않습니다: {ast.dump(node)}")
            else:
                raise ValueError(f"허용되지 않는 AST 노드: {type(node).__name__}")

        tree = ast.parse(expr, mode="eval")
        return bool(_eval_node(tree.body))

    def _preprocess_condition(self, condition: str) -> str:
        """조건 전처리"""
        # 변수 참조 처리 (${var} -> context.get('var'))
        condition = re.sub(
            r"\$\{([^}]+)\}", lambda m: f"context.get('{m.group(1)}', None)", condition
        )

        # 환경변수 참조 처리 ($VAR -> env.get('VAR'))
        condition = re.sub(
            r"\$([A-Z_][A-Z0-9_]*)", lambda m: f"env.get('{m.group(1)}', '')", condition
        )

        # 파일 존재 확인 함수
        condition = re.sub(
            r'file\.exists\([\'"]([^\'"]+)[\'"]\)',
            lambda m: f"__import__('pathlib').Path('{m.group(1)}').exists()",
            condition,
        )

        # 캐시 존재 확인 함수
        condition = re.sub(
            r'cache\.exists\([\'"]([^\'"]+)[\'"]\)',
            lambda m: f"cache.get('{m.group(1)}', False)",
            condition,
        )

        return condition

    def update_context(self, updates: dict[str, Any]):
        """컨텍스트 업데이트"""
        self.context.update(updates)


# 조건 평가 헬퍼 함수들
def check_environment(env_name: str) -> bool:
    """환경 확인"""
    return os.environ.get("ENVIRONMENT") == env_name


def check_profile(profile_name: str, context: dict[str, Any]) -> bool:
    """프로파일 확인"""
    return context.get("profile") == profile_name


def check_app_exists(app_name: str, context: dict[str, Any]) -> bool:
    """앱 존재 확인"""
    apps = context.get("config", {}).get("apps", [])
    return any(app.get("name") == app_name for app in apps)
