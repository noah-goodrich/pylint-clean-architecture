class Stranger:
    def get_data(self) -> 'Stranger':
        return self
    def process(self) -> None:
        pass

def violation_1(obj: Stranger) -> None:
    # VIOLATION: Chaining across two stranger objects
    obj.get_data().get_data().process()

def violation_2(obj: Stranger) -> None:
    # Assigned from method (Stranger)
    data: Stranger = obj.get_data()
    # VIOLATION: data is a stranger, cannot call methods on its internal members
    data.get_data().process()
