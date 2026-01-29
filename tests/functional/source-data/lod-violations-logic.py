class Inner:
    def run(self) -> None:
        return None


class Outer:
    attr: Inner


def violation_3(obj: Outer) -> None:
    # VIOLATION: two-level chain through attr (obj.attr.run). (transformers.py:103, 214)
    obj.attr.run()


class Stranger:
    def get_data(self) -> 'Stranger':
        return self

    def process(self) -> None:
        return None


def violation_1(obj: Stranger) -> None:
    # VIOLATION: Chaining across two stranger objects
    obj.get_data().get_data().process()


def violation_2(obj: Stranger) -> None:
    # Assigned from method (Stranger)
    data: Stranger = obj.get_data()
    # VIOLATION: data is a stranger, cannot call methods on its internal members
    data.get_data().process()
