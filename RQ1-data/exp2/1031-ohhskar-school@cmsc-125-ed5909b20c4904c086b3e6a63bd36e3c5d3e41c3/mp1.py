from random import randint, randrange
from time import sleep
from typing import Optional

MAX_VAL: int = 3
DEBUG: bool = True

Resource = list[Process]
Processes = list[Resource]


class Process:
    def __init__(self, user: int, resource: int, curr_time: Optional[int] = None):
        self._user: int = user
        self._resource: int = resource
        self._curr_time: int = randint(1, MAX_VAL) if curr_time is None else curr_time
        self._time_to_start: int = 0
        self._time_to_end: int = self._curr_time
        self._is_active: bool = False

    def user(self):
        return self._user

    def resource(self):
        return self._resource

    def curr_time(self):
        return self._curr_time

    def time_to_start(self):
        return self._time_to_start

    def time_to_end(self):
        return self._time_to_end

    def activate(self):
        self._is_active: True

    def add_time_to_start(self, time: int):
        self._time_to_start += time
        self._time_to_end += time

    def tick(self):
        self._curr_time -= 1
        if self._curr_time == 0:
            self._is_active = False

    def __str__(self):
        return (
            "[ process ]"
            + "\nUser:           "
            + str(self._user)
            + "\nCurrent Time:   "
            + str(self._curr_time)
            + "\nTime to Use:    "
            + str(self._time_to_start)
            + "\nTime to End:    "
            + str(self._time_to_end)
        ) + "\n"


class OS:
    def __init__(self):
        self._users_count: int = randint(1, MAX_VAL)
        self._resources_count: int = randint(1, MAX_VAL)
        self._active_processes: list[Process] = []
        self._processes: Processes = [
            [None for i in range(self._users_count + 1)]
            for i in range(self._resources_count)
        ]
        self._users_index = [i for i in range(1, self._users_count + 1)]

        if DEBUG:
            self.create_debug_processes()
        else:
            self.create_processes()
        self.calculate_estimated_time()

    def create_debug_processes(self):
        self._users_count = 4
        self._resources_count = 4
        self._processes = [
            [None, Process(1, 1, 3), None, None, None],
            [None, Process(1, 2, 2), None, None, None],
            [None, Process(1, 3, 3), None, None, None],
            [None, Process(2, 4, 3), None, None, None],
        ]

    def create_processes(self):
        for index, resource in enumerate(self._processes, 1):
            max_processes: int = randint(0, self._users_count)
            users_index = self._users_index.copy()

            if DEBUG:
                print("[ create_processes ] max_processes: " + str(max_processes))
                print("[ create_processes ] users_index: " + str(users_index))
                print("[ create_processes ] len(resource): " + str(len(resource)))

            for j in range(max_processes):
                user: int = users_index[randrange(0, len(users_index))]

                resource[user] = Process(user, index)

                users_index.remove(user)

    def calculate_estimated_time(self):
        if DEBUG:
            print("[ calculate_initial_time ] initial processes: \n")
            self.print_processes()

        for user in self._users_index:
            user_processes: list[Process] = []
            for resource in self._processes:
                if resource[user] is not None:
                    self.calculate_tte_in_resource(resource, user)
                    self.check_for_concurrency(user_processes, resource[user])
                    user_processes.append(resource[user])

    def calculate_tte_in_resource(self, resource: Resource, user: int):
        for i in range(user - 1, 0, -1):
            process = resource[i]
            if process is None:
                continue
            else:
                resource[user].add_time_to_start(resource[i].time_to_end())

        if DEBUG:
            print("[ calculate_tte_in_resource ] user: " + str(user))
            print(
                "[ calculate_tte_in_resource ] resource: "
                + str(resource[user].resource())
            )
            print("[ calculate_tte_in_resource ] after calculate:\n")
            self.print_processes()

    def check_for_concurrency(self, user_processes: list[Process], process: Process):
        if DEBUG:
            print("[ check_for_concurrency ] init")
            print("[ check_for_concurrency ] user_process: \n")
            for user_process in user_processes:
                if user_process is not None:
                    print(user_process)
            print("[ check_for_concurrency ] process: \n")
            print(process)
        for user_process in user_processes:
            if user_process.time_to_end() > process.time_to_start():
                print(
                    "[ check_for_concurrency ] user_process.time_to_end(): "
                    + str(user_process.time_to_end())
                )
                print(
                    "[ check_for_concurrency ] process.time_to_start(): "
                    + str(user_process.time_to_start())
                )
                process.add_time_to_start(
                    process.time_to_end() - user_process.time_to_start()
                )

    def print_processes(self):
        for index, resource in enumerate(self._processes, 1):
            print("-" * 20 + "\n\n==| Resource " + str(index) + " |==\n")
            if len(resource) > 0:
                for p in resource:
                    if p is not None:
                        print(p)
            else:
                print("\nNo Processes in Queue\n")
        print("-" * 20)

    def __str__(self):
        return (
            "Users: "
            + str(self._users_count)
            + "\nResources: "
            + str(self._resources_count)
        )


def main():
    if DEBUG:
        print("[ main ] init")
    os: OS = OS()
    print(os)
    if DEBUG:
        print("[ main ] after calculate_estimated_time()")
    os.print_processes()

    # print_init(resource, users)
    # print_after_assign(users)


main()