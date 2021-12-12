from enum import Enum, EnumMeta


class EnumTypesMeta(EnumMeta):
    def __contains__(cls, item):
        try:
            cls(item)
        except ValueError:
            return False
        else:
            return True


class NodeTypes(Enum, metaclass=EnumTypesMeta):
    TASK = 'Task'
    PARALLEL = 'Parallel'
    END = 'End'
    CONDITION = 'Condition'


class TargetTypes(Enum, metaclass=EnumTypesMeta):
    START = 'Start'
    FUNCTION = 'Function'
    CLOUD_FUNCTION = 'CloudFunction'
    DATAFLOW_JOB = 'Dataflow'


class DataflowTemplateType(Enum, metaclass=EnumTypesMeta):
    FLEX = 'Flex'
    CLASSIC = 'Classic'


class TaskStatus(Enum, metaclass=EnumTypesMeta):
    NEW = 'New'
    PENDING = 'Running'
    COMPLETED = 'Completed'
    FAILED = 'Failed'
