from enum import Enum
from copy import deepcopy
from intbase import InterpreterBase, ErrorType

# Enum representing types
class Type(Enum):
    INT = 1
    BOOL = 2
    STRING = 3
    UNKNOWN = 4
    EMPTY = 5

# Function for matching string type to enum
def match_to_enum(type_str):
    match type_str:
        case InterpreterBase.INT_DEF:
            return Type.INT
        case InterpreterBase.BOOL_DEF:
            return Type.BOOL
        case InterpreterBase.STRING_DEF:
            return Type.STRING
        case _:
            return str(type_str)

# Set representing arithmetic operators
arithmetic_operators = {"+", "-", "*", "/", "%"}

# Set representing comparison operators
comparison_operators = {"<", ">", "<=", ">=", "!=", "==", "&", "|"}

# Unary operator
UNARY_OPERATOR = "!"

# Class representing values of variables
class Values:
    def __init__(self, curr_value, obj_type = InterpreterBase.NULL_DEF):
        if isinstance(curr_value, Classes):
            self._type = curr_value.get_name()
            self._curr_value = curr_value
        elif curr_value == InterpreterBase.TRUE_DEF or curr_value == InterpreterBase.FALSE_DEF:
            self._type = Type.BOOL
            if curr_value == InterpreterBase.TRUE_DEF:
                self._curr_value = True
            else:
                self._curr_value = False
        elif curr_value == InterpreterBase.NULL_DEF:
            self._type = str(obj_type)
            self._curr_value = None
        elif curr_value[0] == "\"" and curr_value[-1] == "\"":
            self._type  = Type.STRING
            self._curr_value = curr_value[1:-1]
        elif curr_value.isdigit() or (curr_value[0] == "-" and curr_value[1:].isdigit()):
            self._type  = Type.INT
            self._curr_value = int(curr_value)
        else:
            self._type  = Type.UNKNOWN
            self._curr_value = curr_value
    
    def get_type(self):
        return self._type
    
    def get_curr_value(self):
        return self._curr_value

    def modify_type(self, mod_type):
        self._type = mod_type

# Class representing thrown errors
class ErrorValue:
    def __init__(self, message):
        self._message = message
    
    def convert_to_value(self):
        new_message = "\"" + self._message + "\""
        return Values(new_message)

# Class representing class fields/methods
class Classes:
    def __init__(self, class_name):
        self._class_name = str(class_name)
        self._fields = {}
        self._methods = {}
        self._parent_class = None

    def add_field(self, field, name):
        self._fields[name] = field

    def add_method(self, method, name):
        self._methods[name] = method

    def add_parent(self, parent):
        self._parent_class = deepcopy(parent)

    def get_field(self, field_name):
        if field_name in self._fields:
            return self._fields[field_name]
        return None
    
    def get_method(self, func_name):
        if func_name in self._methods:
            return self._methods[func_name]
        return None
    
    def get_method_from_parent(self, func_name):
        if func_name in self._methods:
            return (self._methods[func_name], self)
        elif self._parent_class == None:
            return None
        else:
            return self._parent_class.get_method_from_parent(func_name)

    def get_parent(self): # return most direct parent
        return self._parent_class

    def get_name(self):
        return self._class_name
    
    def find_parent(self, parent_name):
        if self._parent_class == None:
            return None
        elif self._parent_class._class_name == parent_name:
            return self._parent_class
        else:
            return self._parent_class.find_parent(parent_name)

    def copy_from_other_class(self, other_class):
        self._fields = deepcopy(other_class._fields)
        self._methods = deepcopy(other_class._methods)
        self._parent_class = deepcopy(other_class._parent_class)

# Class representing template classes
class TClass:
    def __init__(self, class_name, types, statements, interpreter):
        self._class_name = str(class_name)
        if len(types) == 0:
            interpreter.error(ErrorType.SYNTAX_ERROR)
        self._types = types
        self._statements = statements

    def num_types(self):
        return len(self._types)

    def create_class(self, arguments, interpreter):
        # create new normal class
        name = arguments
        arguments = arguments.split(InterpreterBase.TYPE_CONCAT_CHAR)
        types = arguments[1:]
        if len(types) != len(self._types):
            interpreter.error(ErrorType.TYPE_ERROR, "invalid type/type mismatch")
        assigned_types = {}
        for i in range(len(types)):
            assigned_types[self._types[i]] = types[i]
            type_val = match_to_enum(types[i])
            if type(type_val) == str and type_val != InterpreterBase.NULL_DEF and  interpreter.environment.get_classes(type_val) == None:
                interpreter.error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch {types[i]}")
        statements = deepcopy(self._statements)
        new_class = Classes(name)

        # parse through template class
        for i in range(len(statements)):
            if statements[i][0] == InterpreterBase.FIELD_DEF:
                # incorrect field creation syntax
                field_len = len(statements[i])
                if field_len < 3:
                    interpreter.error(ErrorType.SYNTAX_ERROR)

                new_field_type = statements[i][1] = str(statements[i][1])
                new_field_name = statements[i][2]

                # check field not declared twice
                if new_class.get_field(new_field_name) != None:
                    interpreter.error(ErrorType.NAME_ERROR, f"{new_field_name} delcared twice")

                # ensure type exists
                for j in assigned_types:
                    statements[i][1] = new_field_type = new_field_type.replace(j, assigned_types[j])
                new_field_type = match_to_enum(new_field_type)
                if type(new_field_type) == str:
                    new_field_type_split = new_field_type.split(InterpreterBase.TYPE_CONCAT_CHAR)
                    field_class = interpreter.environment.get_classes(new_field_type_split[0])
                if type(new_field_type) == str and new_field_type != InterpreterBase.NULL_DEF and field_class == None:
                    interpreter.error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with field {new_field_name}")
                elif type(new_field_type) == str and (len(new_field_type_split) > 1 or isinstance(field_class, TClass)):
                    if field_class.num_types() != len(new_field_type_split) - 1:
                        interpreter.error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with return {new_field_name}")
                    for k in new_field_type_split[1:]:
                        k = match_to_enum(k)
                        if type(k) == str and k != InterpreterBase.NULL_DEF and interpreter.enviornment.get_classes(k) == None:
                            super().error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with variable {new_field_type}")

                # if explicit initialization, verify type matching and add field to environment
                if field_len > 3:
                    new_field_value = statements[i][3]
                    new_field = Values(new_field_value, new_field_type)
                    if new_field_type != new_field.get_type() and not \
                    (new_field_type == interpreter.NULL_DEF and type(new_field.get_type()) == str):
                        interpreter.error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with field {new_field_name}")
                # else default initialization
                else:
                    match new_field_type:
                        case Type.INT:
                            new_field_value = "0"
                        case Type.BOOL:
                            new_field_value = interpreter.FALSE_DEF
                        case Type.STRING:
                            new_field_value = "\"\""
                        case _:
                            new_field_value = interpreter.NULL_DEF
                    new_field = Values(new_field_value, new_field_type)

                new_class.add_field(new_field, new_field_name)
            # method detected
            elif statements[i][0] == InterpreterBase.METHOD_DEF:
                # incorrect method creation syntax
                if len(statements[i]) < 5:
                    interpreter.error(ErrorType.TYPE_ERROR, "Incorrect method declaration")

                new_function_return = statements[i][1]
                new_function_name = statements[i][2]
                new_function_parameters = statements[i][3]
                new_function_statements = statements[i][4]

                # check function not declared twice
                if new_class.get_method(new_function_name) != None:
                    interpreter.error(ErrorType.NAME_ERROR, f"{new_function_name} delcared twice")

                # ensure return type exists
                for j in assigned_types:
                    new_function_return = statements[i][1] = new_function_return.replace(j, assigned_types[j])
                new_function_return = match_to_enum(new_function_return)
                if type(new_function_return) == str:
                    new_function_return_split = new_function_return.split(InterpreterBase.TYPE_CONCAT_CHAR)
                    new_function_class = interpreter.environment.get_classes(new_function_return_split[0])
                if type(new_function_return) == str and new_function_return != InterpreterBase.NULL_DEF and \
                new_function_return != InterpreterBase.VOID_DEF and new_function_class == None:
                    interpreter.error(ErrorType.TYPE_ERROR, f"invalid return type for method {new_function_name}")
                elif type(new_function_return) == str and (len(new_function_return_split) > 1  or isinstance(new_function_class, TClass)):
                    if new_function_class.num_types() != len(new_function_return_split) - 1:
                        interpreter.error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with return {new_function_name}")
                    for k in new_function_return_split[1:]:
                        k = match_to_enum(k)
                        if type(k) == str and k != InterpreterBase.NULL_DEF and interpreter.environment.get_classes(k) == None:
                            interpreter.error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with variable {new_function_return}")

                # convert parameter types
                for j in range(len(new_function_parameters)):
                    for k in assigned_types:
                        statements[i][3][j][0] = new_function_parameters[j][0] = new_function_parameters[j][0].replace(k, assigned_types[k])
                    parameter = match_to_enum(new_function_parameters[j][0])
                    if type(parameter) == str:
                        parameter_split = new_function_parameters[j][0].split(InterpreterBase.TYPE_CONCAT_CHAR)
                        parameter_class = interpreter.environment.get_classes(parameter_split[0])
                    if type(parameter) == str and parameter != InterpreterBase.NULL_DEF and parameter_class == None:
                        interpreter.error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with return {new_function_parameters[j][1]}")
                    elif type(parameter) == str and (len(parameter_split) > 1 or isinstance(parameter_class, TClass)):
                        if parameter_class.num_types() != len(parameter_split) - 1:
                            interpreter.error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with return {new_function_parameters[j][1]}")
                        for k in parameter_split[1:]:
                            k = match_to_enum(k)
                            if type(k) == str and k != InterpreterBase.NULL_DEF and interpreter.environment.get_classes(k) == None:
                                interpreter.error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with variable {parameter_split[0]}")

                # convert statement types
                def convert_statement(statements, assigned_types):
                    for i in range(len(statements)):
                        if type(statements[i]) == list:
                            statements[i] = convert_statement(statements[i], assigned_types)
                        else:
                            for j in assigned_types:
                                statements[i] = str(statements[i])
                                statements[i] = statements[i].replace(j, assigned_types[j])
                    return statements

                statements[i][4] = new_function_statements = convert_statement(statements[i][4], assigned_types)
                        
                # add function to environment
                new_function = Functions(new_function_return, new_function_name, new_function_parameters, new_function_statements)
                new_class.add_method(new_function, new_function_name)
        return new_class

# Class representing function name, parameters, and statements
class Functions:
    def __init__(self, return_type, name, parameters, statements):
        self._return_type = return_type
        self._name = name
        self._parameters = parameters
        self._statements = statements

    def list_parameters(self):
        return self._parameters
    
    def list_statements(self):
        return self._statements
    
    def get_return_type(self):
        return self._return_type
    
    def get_name(self):
        return self._name

# Environment class tracking all objects
class Environment:
    def __init__(self):
        self._classes = {}
        self._main_class = None

    def get_classes(self, class_name):
        if class_name in self._classes:
            return self._classes[class_name]
        return None

    def set_class(self, class_name, curr_class):
        self._classes[class_name] = curr_class
    
    def get_main_class(self):
        if self._main_class == None:
            main_class = self.get_classes(InterpreterBase.MAIN_CLASS_DEF) 
            if main_class == None:
                return None
            self._main_class = Classes(InterpreterBase.MAIN_CLASS_DEF)
            self._main_class.copy_from_other_class(main_class)
        return self._main_class