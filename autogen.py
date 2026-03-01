```python
class NewAuto:
    def __init__(self, make: str, model: str, year: int):
        self.make = make
        self.model = model
        self.year = year

    def __repr__(self):
        return f"NewAuto(make={self.make!r}, model={self.model!r}, year={self.year!r})"

    def age(self, current_year: int) -> int:
        return current_year - self.year
```