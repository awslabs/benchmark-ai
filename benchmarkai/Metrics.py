class Metrics:
    def __init__(self, name, unit):
        self.name = name
        self.unit = unit

    def __repr__(self):
        return f'{self.name}({self.unit})'
