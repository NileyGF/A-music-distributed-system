from multiprocessing import Process, Value, Array, Manager
class A:
    pass
class B:
    pass
class MyClass:
    def __init__(self):
        self.my_variable = Value('i', 0)  # 'i' indicates an integer value
        manager = Manager()
        self.shared_list = manager.list()  # Create a shared list
        self.shared_list.append(['172.20.0.0',9999])
        self.shared_list.append(['172.20.0.1',9999])
        self.shared_list.append(['172.20.0.2',9999])
        self.role = manager.list()
        self.role.append(A())
        processes = []

        for _ in range(2):
            p = Process(target=self.modify_variable)
            processes.append(p)
            p.start()

        for p in processes:
            p.join()
            
        for _ in range(2):
            p = Process(target=self.modify_variable)
            processes.append(p)
            p.start()
        for p in processes:
            p.join()

    def modify_variable(self):
        self.my_variable.value += 1
        self.shared_list[0] = ['172.20.0.0',9669]
        print(self.role)
        p = Process(target=self.sub_sub)
        p.start()
        p.join()

    def sub_sub(self):
        # print(self.shared_list)
        self.shared_list[1] = ['172.20.0.7',9669]
        # print(self.shared_list)
        self.role[0] = B()
        print(self.role)

my_object = MyClass()


print(my_object.my_variable.value)  # Output: 5
print(tuple(my_object.shared_list))
print(my_object.role)

