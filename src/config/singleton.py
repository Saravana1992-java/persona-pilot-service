class SingletonMeta(type):
    """
        Metaclass for implementing the Singleton design pattern.

        Attributes:
        _instances (dict): A dictionary that holds the instances of the classes. The key is the class and the
        value is the instance of the class.
        """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        """
            Creates a new instance of the class or returns an existing one.

            This method overrides the default behavior of a class's call method. When a class with SingletonMeta
            as its metaclass is called,
            this method checks if an instance of the class already exists. If it does, it returns the existing instance.
            If it doesn't, it creates a new instance and stores it in the _instances dictionary before returning it.

            Parameters:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

            Returns:
            object: An instance of the class.
            """
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]
