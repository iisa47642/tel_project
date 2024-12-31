class TaskManagerInstance:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            raise RuntimeError("TaskManager not initialized")
        return cls._instance

    @classmethod
    def set_instance(cls, instance):
        cls._instance = instance

    @classmethod
    def is_initialized(cls):
        return cls._instance is not None
