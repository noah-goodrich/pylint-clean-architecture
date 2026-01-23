from typing import Self

class DataFrame:
    def select(self, *args: str) -> Self:
        return self
    def filter(self, condition: str) -> Self:
        return self
    def group_by(self, column: str) -> Self:
        return self
    def count(self) -> int:
        return 1

def fluent_api_exemption(df: DataFrame) -> None:
    # Allowed: Self-returning methods (Fluent API)
    _res: int = df.select("a").filter("b > 0").group_by("c").count()
