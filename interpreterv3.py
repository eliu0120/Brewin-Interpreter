from intbase import ErrorType, InterpreterBase
from bparser import BParser
import environment as env
from copy import copy

# Interpreter
class Interpreter(InterpreterBase):
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
    
    # runs interpreter
    def run(self, program):
        result, self.parsed_program = BParser.parse(program)
        if result == False:
            return
        self.environment = env.Environment()
        self.discover_classes()
        self.run_main()
    
    # discovers classes in program
    def discover_classes(self):
        # detect all class names
        for i in self.parsed_program:
            if i[0] == super().CLASS_DEF or i[0] == super().TEMPLATE_CLASS_DEF:
                # check class not declared twice
                new_class_name = i[1]
                if self.environment.get_classes(new_class_name) != None:
                    super().error(ErrorType.TYPE_ERROR, f"{new_class_name} delcared twice")
                
                if i[0] == super().CLASS_DEF:
                    if new_class_name.find(super().TYPE_CONCAT_CHAR) != -1:
                        super().error(ErrorType.SYNTAX_ERROR)
                    new_class = env.Classes(new_class_name)
                else:
                    new_class = env.TClass(new_class_name, i[2], i[3:], self)
                self.environment.set_class(new_class_name, new_class)
            
        # fill in normal classes
        for i in self.parsed_program:
            if i[0] == super().CLASS_DEF:
                new_class_name = i[1]
                new_class = self.environment.get_classes(new_class_name)

                # check if class is inherited, add parent class
                if i[2] == super().INHERITS_DEF:
                    parent_class_name = i[3]
                    parent_class = self.environment.get_classes(parent_class_name)
                    if parent_class == None or isinstance(parent_class, env.TClass):
                        super().error(ErrorType.TYPE_ERROR, f"No class named {parent_class_name} found")
                    new_class.add_parent(parent_class)
                    body = i[4:]
                else:
                    body = i[2:]

                # iterate through class, detect fields and methods
                for j in body:
                    # field detected
                    if j[0] == super().FIELD_DEF:
                        # incorrect field creation syntax
                        field_len = len(j)
                        if field_len < 3:
                            super().error(ErrorType.SYNTAX_ERROR)

                        new_field_type = j[1]
                        new_field_name = j[2]

                        # check field not declared twice
                        if new_class.get_field(new_field_name) != None:
                            super().error(ErrorType.NAME_ERROR, f"{new_field_name} delcared twice")

                        # ensure type exists
                        new_field_type = env.match_to_enum(new_field_type)
                        if type(new_field_type) == str:
                            new_field_type_split = new_field_type.split(super().TYPE_CONCAT_CHAR)
                            field_class = self.environment.get_classes(new_field_type_split[0])
                        if type(new_field_type) == str and new_field_type != super().NULL_DEF and field_class == None:
                            super().error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with field {new_field_name}")
                        elif type(new_field_type) == str and (len(new_field_type_split) > 1 or isinstance(field_class, env.TClass)):
                            if field_class.num_types() != len(new_field_type_split) - 1:
                                super().error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with return {new_field_name}")
                            for k in new_field_type_split[1:]:
                                k = env.match_to_enum(k)
                                if type(k) == str and k != super().NULL_DEF and  self.environment.get_classes(k) == None:
                                    super().error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with variable {new_field_type}")
                        
                        # if explicit initialization, verify type matching and add field to environment
                        if field_len > 3:
                            new_field_value = j[3]
                            new_field = env.Values(new_field_value, new_field_type)
                            if new_field_type != new_field.get_type() and not \
                            (new_field_type == super().NULL_DEF and type(new_field.get_type()) == str):
                                super().error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with field {new_field_name}")
                        # else default initialization
                        else:
                            match new_field_type:
                                case env.Type.INT:
                                    new_field_value = "0"
                                case env.Type.BOOL:
                                    new_field_value = super().FALSE_DEF
                                case env.Type.STRING:
                                    new_field_value = "\"\""
                                case _:
                                    new_field_value = super().NULL_DEF
                            new_field = env.Values(new_field_value, new_field_type)

                        new_class.add_field(new_field, new_field_name)

                    # method detected
                    elif j[0] == super().METHOD_DEF:
                        # incorrect method creation syntax
                        if len(j) < 4:
                            super().error(ErrorType.TYPE_ERROR, "Incorrect method declaration")

                        new_function_return = env.match_to_enum(j[1])
                        new_function_name = j[2]
                        new_function_parameters = j[3]
                        new_function_statements = j[4]

                        # check function not declared twice
                        if new_class.get_method(new_function_name) != None:
                            super().error(ErrorType.NAME_ERROR, f"{new_function_name} delcared twice")

                        # ensure return type exists
                        if type(new_function_return) == str:
                            new_function_return_split = new_function_return.split(super().TYPE_CONCAT_CHAR)
                            new_function_class = self.environment.get_classes(new_function_return_split[0])
                        if type(new_function_return) == str and new_function_return != super().NULL_DEF and \
                        new_function_return != super().VOID_DEF and new_function_class == None:
                            super().error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with return {new_function_name}")
                        elif type(new_function_return) == str and (len(new_function_return_split) > 1 \
                        or isinstance(new_function_class, env.TClass)):
                            if new_function_class.num_types() != len(new_function_return_split) - 1:
                                super().error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with return {new_function_name}")
                            for k in new_function_return_split[1:]:
                                k = env.match_to_enum(k)
                                if type(k) == str and k != super().NULL_DEF and self.environment.get_classes(k) == None:
                                    super().error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with variable {new_function_return}")
                        
                        # ensure parameters exists
                        for k in new_function_parameters:
                            parameter = env.match_to_enum(k[0])
                            if type(parameter) == str:
                                parameter_split = k[0].split(super().TYPE_CONCAT_CHAR)
                                parameter_class = self.environment.get_classes(parameter_split[0])
                            if type(parameter) == str and parameter != super().NULL_DEF and parameter_class == None:
                                super().error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with return {k[1]}")
                            elif type(parameter) == str and (len(parameter_split) > 1 or isinstance(parameter_class, env.TClass)):
                                if parameter_class.num_types() != len(parameter_split) - 1:
                                    super().error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with return {k[1]}")
                                for l in parameter_split[1:]:
                                    l = env.match_to_enum(l)
                                    if type(l) == str and l != super().NULL_DEF and self.environment.get_classes(l) == None:
                                        super().error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with variable {parameter_split[0]}")
                        
                        # add function to environment
                        new_function = env.Functions(new_function_return, new_function_name, new_function_parameters, new_function_statements)
                        new_class.add_method(new_function, new_function_name)

        # Ensure main class exists
        main_class = self.environment.get_main_class()
        if main_class == None or isinstance(main_class, env.TClass):
            super().error(ErrorType.TYPE_ERROR, "No class named main found")

        # Execution successful    
        return
    
    # Run through main class to find main function
    def run_main(self):
        main_class = self.environment.get_main_class()
        main_method = main_class.get_method(super().MAIN_FUNC_DEF)
        if main_method == None:
            super().error(ErrorType.NAME_ERROR, "unknown method main")
        if len(main_method.list_parameters()) > 0:
            super().error(ErrorType.TYPE_ERROR, "invalid number of parameters in call to main")
        self.run_function(main_method, main_class)
    
    # Run function
    def run_function(self, function, class_obj, arguments = [], original_class_obj = None):
        # Get information regarding function
        return_type = function.get_return_type()
        name = function.get_name()
        statements = function.list_statements()
        parameters = function.list_parameters()
        if len(parameters) != len(arguments):
            parent_class = class_obj.get_parent()
            if parent_class == None:
                super().error(ErrorType.NAME_ERROR, f"unknown method {name}")
            find_parent_func = parent_class.get_method_from_parent(name)
            if find_parent_func == None:
                super().error(ErrorType.NAME_ERROR, f"unknown method {name}")
            parent_func, parent_class = find_parent_func
            return self.run_function(parent_func, parent_class, arguments, original_class_obj)

        # Check arguments are valid
        new_parameters = {}
        original_arguments = copy(arguments)
        for i in range(len(arguments)):
            if isinstance(arguments[i], tuple):
                arguments[i] = env.Values(arguments[i][0], arguments[i][1])
            else:
                arguments[i] = env.Values(arguments[i])
            parameter_type = env.match_to_enum(parameters[i][0])

            if parameter_type != arguments[i].get_type() and parameter_type != super().NULL_DEF and not \
            (arguments[i] == super().NULL_DEF and type(parameter_type.get_type()) == str):
                if type(arguments[i].get_type()) != str or \
                self.environment.get_classes(arguments[i].get_type()).find_parent(parameter_type) == None:
                    parent_class = class_obj.get_parent()
                    if parent_class == None:
                        super().error(ErrorType.NAME_ERROR, f"unknown method {name}")
                    find_parent_func = parent_class.get_method_from_parent(name)
                    if find_parent_func == None:
                        super().error(ErrorType.NAME_ERROR, f"unknown method {name}")
                    parent_func, parent_class = find_parent_func
                    return self.run_function(parent_func, parent_class, original_arguments)
                else:
                    arguments[i].modify_type(parameter_type)
            
            # Check for duplicate parameters
            if parameters[i][1] in new_parameters:
                super().error(ErrorType.NAME_ERROR, f"unknown method {name}")
            new_parameters[parameters[i][1]] = arguments[i]
        
        # Run statements in function
        output = self.run_statement(statements, new_parameters, class_obj, original_class_obj)

        # Error thrown
        if isinstance(output, env.ErrorValue):
            return output
        
        # Default return value
        if output == None or output == env.Type.EMPTY or \
        (statements[0] != super().BEGIN_DEF and statements[0] != super().RETURN_DEF and statements[0] != super().LET_DEF and \
         statements[0] != super().IF_DEF and statements[0] != super().WHILE_DEF and statements[0] != super().TRY_DEF):
            match return_type:
                case env.Type.INT:
                    return 0
                case env.Type.BOOL:
                    return False
                case env.Type.STRING:
                    return ""
                case self.VOID_DEF:
                    return env.Type.EMPTY
                case self.NULL_DEF:
                    return env.Values(super().NULL_DEF, return_type)
                case _:
                    if self.environment.get_classes(return_type) == None:
                        super().error(ErrorType.TYPE_ERROR, f"invalid return type for {name}")
                    return env.Values(super().NULL_DEF, return_type)
        # Ensure return value types match
        elif isinstance(output, env.Values) and return_type != self.VOID_DEF:
            output.modify_type(return_type)
            return output
        else:
            match return_type:
                case env.Type.INT:
                    if type(output) == int:
                        return output
                case env.Type.BOOL:
                    if type(output) == bool:
                        return output
                case env.Type.STRING:
                    if type(output) == str:
                        return output
                case self.NULL_DEF | self.VOID_DEF:
                    super().error(ErrorType.TYPE_ERROR, f"type mismatch {return_type} and {type(output)}")
                case _:
                    if output.get_name() == return_type or output.find_parent(return_type) != None:
                        return output
        # Return output
        super().error(ErrorType.TYPE_ERROR, f"type mismatch {return_type} and {type(output)}")

    # Handles statements in a function
    def run_statement(self, statements, parameters, class_obj, original_class_obj = None):
        output = None # None if retusrn statement not called
        match statements[0]:
            case self.PRINT_DEF:
                output = self.print_statement(statements[1:], parameters, class_obj, original_class_obj)
            case self.BEGIN_DEF:
                output = self.begin_statement(statements[1:], parameters, class_obj, original_class_obj)
            case self.RETURN_DEF:
                output = self.return_statement(parameters, class_obj, statements[1:],  original_class_obj)
            case self.SET_DEF:
                output = self.handle_set(statements[1:], parameters, class_obj, original_class_obj)
            case self.CALL_DEF:
                output = self.handle_call(statements[1:], parameters, class_obj, original_class_obj)
            case self.INPUT_INT_DEF:
                output = self.handle_inputi(statements[1:], parameters, class_obj)
            case self.INPUT_STRING_DEF:
                output = self.handle_inputs(statements[1:], parameters, class_obj)
            case self.IF_DEF:
                output = self.handle_if(statements[1:], parameters, class_obj, original_class_obj)
            case self.WHILE_DEF:
                output = self.handle_while(statements[1:], parameters, class_obj, original_class_obj)
            case self.LET_DEF:
                output = self.handle_let(statements[1], statements[2:], parameters, class_obj, original_class_obj)
            case self.THROW_DEF:
                output = self.handle_throw(statements[1:], parameters, class_obj, original_class_obj)
            case self.TRY_DEF:
                output = self.handle_try(statements[1:], parameters, class_obj, original_class_obj)
            case _:
                super().error(ErrorType.SYNTAX_ERROR, f"unknown statement {statements[0]}")
        return output

    # Print statement
    def print_statement(self, arguments, parameters, class_obj, original_class_obj = None):
        output = ""

        def argument_handler(self, argument, parameters, class_obj, output, original_class_obj = None):
            if argument[0] == "\"" and argument[-1] == "\"":
                output += argument[1:-1]
            elif isinstance(argument, list):
                if argument[0] in env.arithmetic_operators:
                    ret_val = self.handle_arithmetic(argument, parameters, class_obj, original_class_obj)
                    if isinstance(ret_val, env.ErrorValue):
                        return ret_val
                    output += str(ret_val)
                elif argument[0] in env.comparison_operators:
                    ret_val = self.handle_comparison(argument, parameters, class_obj, original_class_obj)
                    if isinstance(ret_val, env.ErrorValue):
                        return ret_val
                    output += str(ret_val).lower()
                elif argument[0] == env.UNARY_OPERATOR:
                    ret_val = self.handle_unary(argument, parameters, class_obj, original_class_obj)
                    if isinstance(ret_val, env.ErrorValue):
                        return ret_val
                    output += str(ret_val).lower()
                elif argument[0] == super().CALL_DEF:
                    ret_val = self.handle_call(argument[1:], parameters, class_obj, original_class_obj)
                    if isinstance(ret_val, env.ErrorValue):
                        return ret_val
                    if isinstance(ret_val, env.Values) or ret_val == env.Type.EMPTY:
                        ret_val = "None"
                    else:
                        ret_val = str(ret_val)
                    if ret_val.lower() == super().TRUE_DEF or ret_val.lower() == super().FALSE_DEF:
                        ret_val = ret_val.lower()
                    output += ret_val
                elif argument[0] == super().NEW_DEF:
                    ret_val = self.handle_new(argument[1:])
                    output += str(ret_val)
                else:
                    super().error(ErrorType.SYNTAX_ERROR)
            elif argument == super().TRUE_DEF or argument == super().FALSE_DEF or \
            (argument.isdigit() or (argument[0] == "-" and argument[1:].isdigit())):
                output += argument
            elif argument == super().NULL_DEF:
                output += "None"
            elif argument in parameters or class_obj.get_field(argument) != None:
                if argument in parameters:
                    value = parameters[argument]
                else:
                    value = class_obj.get_field(argument)
                if value.get_type() == env.Type.UNKNOWN:
                    super().error(ErrorType.SYNTAX_ERROR)
                if value.get_type() == env.Type.BOOL:
                    output += str(value.get_curr_value()).lower()
                else:
                    output += str(value.get_curr_value())
            else:
                super().error(ErrorType.NAME_ERROR, f"invalid field or parameter {argument}")
            return output

        for i in arguments:
            output = argument_handler(self, i, parameters, class_obj, output, original_class_obj)
            if isinstance(output, env.ErrorValue):
                return output
        super().output(output)
        return None
    
    # Begin statment
    def begin_statement(self, statements, parameters, class_obj, original_class_obj = None):
        for i in statements:
            output = self.run_statement(i, parameters, class_obj, original_class_obj)
            # A return or throw statement has been called somewhere
            if isinstance(output, env.ErrorValue) or (output != None and i[0] != super().CALL_DEF):
                return output
            elif i[0] == super().CALL_DEF:
                output = None
        return None

    # Let statement
    def handle_let(self, local_vars, statements, parameters, class_obj, original_class_obj = None):
        # create new local bindings
        mod_parameters = copy(parameters)
        local_vars_names = set()
        for i in local_vars:
            var_len = len(i)
            if var_len < 2:
                super().error(ErrorType.SYNTAX_ERROR)

            new_var_type = i[0]
            new_var_name = i[1]

            # ensure no duplicate local vars
            if new_var_name in local_vars_names:
                super().error(ErrorType.NAME_ERROR, f"duplicate local variable name {new_var_name}")
            
            # verify type exists
            new_var_type = env.match_to_enum(new_var_type)
            if type(new_var_type) == str:
                new_var_type_split = new_var_type.split(super().TYPE_CONCAT_CHAR)
                new_var_class = self.environment.get_classes(new_var_type_split[0])
            if type(new_var_type) == str and new_var_type != super().NULL_DEF and new_var_class == None:
                super().error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with variable {new_var_name}")
            elif type(new_var_type) == str and (len(new_var_type_split) > 1 or isinstance(new_var_class, env.TClass)):
                if new_var_class.num_types() != len(new_var_type_split) - 1:
                    super().error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with variable {new_var_name}")
                for j in new_var_type_split[1:]:
                    j = env.match_to_enum(j)
                    if type(j) == str and j != super().NULL_DEF and self.environment.get_classes(j.split(super().TYPE_CONCAT_CHAR)[0]) == None:
                        super().error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with variable {new_var_type}")

            # if explicit intialization, verify type matching
            if var_len > 2:
                new_var_value = i[2]
                new_var = env.Values(new_var_value, new_var_type)
                if new_var_type != new_var.get_type() and not  (new_var_type == super().NULL_DEF and type(new_var.get_type()) == str):
                    super().error(ErrorType.TYPE_ERROR, f"invalid type/type mismatch with field {new_var_name}")
            # else default initialization
            else:
                match new_var_type:
                    case env.Type.INT:
                        new_var_value = "0"
                    case env.Type.BOOL:
                        new_var_value = super().FALSE_DEF
                    case env.Type.STRING:
                        new_var_value = "\"\""
                    case _:
                        new_var_value = super().NULL_DEF
                new_var = env.Values(new_var_value, new_var_type)
            
            local_vars_names.add(new_var_name)
            mod_parameters[new_var_name] = new_var
        
        # run statements
        for i in statements:
            output = self.run_statement(i, mod_parameters, class_obj, original_class_obj)
            # A return statement has been called somewhere
            if isinstance(output, env.ErrorValue) or (output != None and i[0] != super().CALL_DEF):
                for i in parameters:
                    if i not in local_vars_names:
                        parameters[i] = mod_parameters[i]
                return output
            elif i[0] == super().CALL_DEF:
                output = None

        for i in parameters:
            if i not in local_vars_names:
                parameters[i] = mod_parameters[i]
        return None
    
    # Throw statement
    # Returns an error value
    def handle_throw(self, arguments, parameters, class_obj, original_class_obj = None):
        if len(arguments) == 0:
            super().error(ErrorType.SYNTAX_ERROR)
        arguments = arguments[0]
        if isinstance(arguments, list):
            if arguments[0] in env.arithmetic_operators:
                arguments = self.handle_arithmetic(arguments, parameters, class_obj, original_class_obj) 
            elif arguments[0] in env.comparison_operators:
                arguments = self.handle_comparison(arguments, parameters, class_obj, original_class_obj) 
            elif arguments[0] == env.UNARY_OPERATOR:
                arguments = self.handle_unary(arguments, parameters, class_obj, original_class_obj) 
            elif arguments[0] == super().CALL_DEF:
                arguments = self.handle_call(arguments[1:], parameters, class_obj, original_class_obj)
            elif arguments[0] == super().NEW_DEF:
                arguments = self.handle_new(arguments[1:])
            else:
                super().error(ErrorType.SYNTAX_ERROR)
            if isinstance(arguments, env.ErrorValue):
                return arguments
        elif arguments in parameters or class_obj.get_field(arguments) != None:
            if arguments in parameters:
                return_val = parameters[arguments]
            else:
                return_val = class_obj.get_field(arguments)
            if return_val.get_type() == env.Type.UNKNOWN:
                super().error(ErrorType.SYNTAX_ERROR)
            arguments = return_val.get_curr_value() # returns true value
        elif arguments == super().TRUE_DEF:
            arguments = True
        elif arguments == super().FALSE_DEF:
            arguments = False
        elif arguments == super().NULL_DEF:
            arguments = env.Values(super().NULL_DEF)
        elif arguments.isdigit() or (arguments[0] == "-" and arguments[1:].isdigit()):
            arguments = int(arguments)
        elif arguments[0] == "\"" and arguments[-1] == "\"":
            arguments = arguments[1:-1]
        elif arguments == super().ME_DEF:
            arguments = class_obj
        else:
            super().error(ErrorType.NAME_ERROR, f"invalid field or parameter {arguments}")

        if type(arguments) != str:
            super().error(ErrorType.TYPE_ERROR, "non-string thrown")
        return env.ErrorValue(arguments)

    # Try statement
    # Returns None
    def handle_try(self, arguments, parameters, class_obj, original_class_obj = None):
        if len(arguments) == 0:
            super().error(ErrorType.SYNTAX_ERROR)
        arguments = arguments[0:2]
        if type(arguments[0]) != list:
            super().error(ErrorType.SYNTAX_ERROR)
        output = self.run_statement(arguments[0], parameters, class_obj, original_class_obj)
        if not isinstance(output, env.ErrorValue):
            if arguments[0][0] != super().CALL_DEF:
                return output
            else:
                return None
        mod_parameters = copy(parameters)
        mod_parameters[super().EXCEPTION_VARIABLE_DEF] = output.convert_to_value()
        if len(arguments) < 2 or type(arguments[1]) != list:
            super().error(ErrorType.SYNTAX_ERROR)
        output = self.run_statement(arguments[1], mod_parameters, class_obj, original_class_obj)
        if arguments[1][0] != super().CALL_DEF:
            return output
        else:
            return None
    
    # Return statement
    # Return value depends on function called, should return true value
    def return_statement(self, parameters, class_obj, arguments = [], original_class_obj = None):
        if len(arguments) == 0:
            return env.Type.EMPTY
        arguments = arguments[0]
        if isinstance(arguments, list):
            if arguments[0] in env.arithmetic_operators:
                return self.handle_arithmetic(arguments, parameters, class_obj, original_class_obj) # returns int or string
            elif arguments[0] in env.comparison_operators:
                return self.handle_comparison(arguments, parameters, class_obj, original_class_obj) # returns bool
            elif arguments[0] == env.UNARY_OPERATOR:
                return self.handle_unary(arguments, parameters, class_obj, original_class_obj) # returns bool
            elif arguments[0] == super().CALL_DEF:
                return self.handle_call(arguments[1:], parameters, class_obj, original_class_obj)
            elif arguments[0] == super().NEW_DEF:
                return self.handle_new(arguments[1:])
            super().error(ErrorType.SYNTAX_ERROR)
        elif arguments in parameters or class_obj.get_field(arguments) != None:
            if arguments in parameters:
                return_val = parameters[arguments]
            else:
                return_val = class_obj.get_field(arguments)
            if return_val.get_type() == env.Type.UNKNOWN:
                super().error(ErrorType.SYNTAX_ERROR)
            return return_val.get_curr_value() # returns true value
        elif arguments == super().TRUE_DEF:
            return True
        elif arguments == super().FALSE_DEF:
            return False
        elif arguments == super().NULL_DEF:
            return env.Values(super().NULL_DEF)
        elif arguments.isdigit() or (arguments[0] == "-" and arguments[1:].isdigit()):
            return int(arguments)
        elif arguments[0] == "\"" and arguments[-1] == "\"":
            return arguments[1:-1]
        elif arguments == super().ME_DEF:
            return class_obj
        else:
            super().error(ErrorType.NAME_ERROR, f"invalid field or parameter {arguments}")
        return arguments
    
    # Handle arithmetic operators
    # RETURN VALUE: int or string value
    def handle_arithmetic(self, arguments, parameters, class_obj, original_class_obj = None):
        # Ensure correct # of arguments called
        if len(arguments) < 3:
            super().error(ErrorType.SYNTAX_ERROR, "invalid number of parameters for operator")
        elif len(arguments) > 3:
            arguments = arguments[0:3]
        
        operands = arguments[1:3]
        # Get arguments
        for i in [0, 1]:
            if isinstance(operands[i], list):
                if operands[i][0] in env.arithmetic_operators:
                    operands[i] = self.handle_arithmetic(operands[i], parameters, class_obj, original_class_obj)
                elif operands[i][0] in env.comparison_operators:
                    operands[i] = self.handle_comparison(operands[i], parameters, class_obj, original_class_obj)
                elif operands[i][0] == env.UNARY_OPERATOR:
                    operands[i] = self.handle_unary(operands[i], parameters, class_obj, original_class_obj)
                elif operands[i][0] == super().CALL_DEF:
                    operands[i] = self.handle_call(operands[i][1:], parameters, class_obj, original_class_obj)
                elif operands[i][0] == super().NEW_DEF:
                    operands[i] = self.handle_new(operands[i][1:])
                else:
                    super().error(ErrorType.SYNTAX_ERROR)
                if isinstance(operands[i], env.ErrorValue):
                    return operands[i]
            elif operands[i] in parameters or class_obj.get_field(operands[i]) != None:
                if operands[i] in parameters:
                    operands[i] = parameters[operands[i]]
                else:
                    operands[i] = class_obj.get_field(operands[i])
                if operands[i].get_type() == env.Type.UNKNOWN:
                    super().error(ErrorType.SYNTAX_ERROR)
                operands[i] = operands[i].get_curr_value()
            elif operands[i].isdigit() or (operands[i][0] == "-" and operands[i]):
                operands[i] = int(operands[i])
            elif operands[i][0] == "\"" and operands[i][-1] == "\"":
                operands[i] = operands[i][1:-1]
            elif operands[i] == super().TRUE_DEF or operands[i] == super().FALSE_DEF or operands[i] == super().NULL_DEF:
                super().error(ErrorType.TYPE_ERROR, "invalid operator applied to class")
            else:
                super().error(ErrorType.NAME_ERROR, f"invalid field or parameter {operands[i]}")             
        if type(operands[0]) != type(operands[1]):
            super().error(ErrorType.TYPE_ERROR, f"operator {arguments[0]} applied to two incompatible types")

        # Compute arguments
        match arguments[0]:
            case "+":
                if type(operands[0]) != int and type(operands[0]) != str:
                    super().error(ErrorType.TYPE_ERROR, "invalid operator applied to class")
                return operands[0] + operands[1]
            case "*":
                if type(operands[0]) != int:
                    super().error(ErrorType.TYPE_ERROR, "invalid operator applied to class")
                return operands[0] * operands[1]
            case "-":
                if type(operands[0]) != int:
                    super().error(ErrorType.TYPE_ERROR, "invalid operator applied to class")
                return operands[0] - operands[1]
            case "/":
                if type(operands[0]) != int:
                    super().error(ErrorType.TYPE_ERROR, "invalid operator applied to class")
                if operands[1] == 0:
                    super().error(ErrorType.SYNTAX_ERROR, "divide by 0 error")
                return int(operands[0] / operands[1])
            case "%":
                if type(operands[0]) != int:
                    super().error(ErrorType.TYPE_ERROR, "invalid operator applied to class")
                if operands[1] == 0:
                    super().error(ErrorType.SYNTAX_ERROR, "mod by 0 error")
                return operands[0] % operands[1]
        return None

    # Handle comparison operators
    # RETURN VALUE: bool value
    def handle_comparison(self, arguments, parameters, class_obj, original_class_obj = None):
        # Ensure correct # of arguments called
        if len(arguments) < 3:
            super().error(ErrorType.SYNTAX_ERROR, "invalid number of parameters for operator")
        elif len(arguments) > 3:
            arguments = arguments[0:3]

        operands = arguments[1:3]
        # Get arguments
        for i in [0, 1]:
            if isinstance(operands[i], list):
                if operands[i][0] in env.arithmetic_operators:
                    operands[i] = self.handle_arithmetic(operands[i], parameters, class_obj, original_class_obj)
                elif operands[i][0] in env.comparison_operators:
                    operands[i] = self.handle_comparison(operands[i], parameters, class_obj, original_class_obj)
                elif operands[i][0] == env.UNARY_OPERATOR:
                    operands[i] = self.handle_unary(operands[i], parameters, class_obj, original_class_obj)
                elif operands[i][0] == super().CALL_DEF:
                    operands[i] = self.handle_call(operands[i][1:], parameters, class_obj, original_class_obj)
                    if isinstance(operands[i], env.Values):
                        operands[i] = (None, operands[i].get_type())
                elif operands[i][0] == super().NEW_DEF:
                    operands[i] = self.handle_new(operands[i][1:])
                else:
                    super().error(ErrorType.SYNTAX_ERROR)
                if isinstance(operands[i], env.ErrorValue):
                    return operands[i]
            elif operands[i] in parameters or class_obj.get_field(operands[i]) != None:
                if operands[i] in parameters:
                    operands[i] = parameters[operands[i]]
                else:
                    operands[i] = class_obj.get_field(operands[i])
                if operands[i].get_type() == env.Type.UNKNOWN:
                    super().error(ErrorType.SYNTAX_ERROR)
                else:
                    operand_value = operands[i].get_curr_value()
                    if operand_value == None:
                        operands[i] = (operand_value, operands[i].get_type())
                    else:
                        operands[i] = operand_value
            elif operands[i].isdigit() or (operands[i][0] == "-" and operands[i][1:].isdigit()):
                operands[i] = int(operands[i])
            elif operands[i][0] == "\"" and operands[i][-1] == "\"":
                operands[i] = operands[i][1:-1]
            elif type(operands[i]) == bool or operands[i] == super().TRUE_DEF or operands[i] == super().FALSE_DEF:
                if operands[i] == super().TRUE_DEF:
                    operands[i] = True
                else:
                    operands[i] = False
            elif operands[i] == super().NULL_DEF:
                operands[i] = (None, super().NULL_DEF)
            else:
                super().error(ErrorType.NAME_ERROR, f"invalid field or parameter {operands[i]}")    
        if type(operands[0]) != type(operands[1]) and not ((type(operands[0]) == tuple and isinstance(operands[1], env.Classes)) or \
            (type(operands[1]) == tuple and isinstance(operands[0], env.Classes))):
            super().error(ErrorType.TYPE_ERROR, f"operator {arguments[0]} applied to two incompatible types")
        elif isinstance(operands[0], env.Classes) and isinstance(operands[1], env.Classes):
            name0 = operands[0].get_name()
            name1 = operands[1].get_name()
            if operands[0].find_parent(name1) == None and operands[1].find_parent(name0) == None and name0 != name1:
                super().error(ErrorType.TYPE_ERROR, f"operator {arguments[0]} applied to two incompatible types")
        elif isinstance(operands[0], tuple) and isinstance(operands[1], env.Classes):
            name0 = operands[0][1]
            name1 = operands[1].get_name()
            if name0 == super().NULL_DEF or name0 == name1 or operands[1].find_parent(name0) != None:
                operands[0] = operands[0][0]
            elif name1.find(super().TYPE_CONCAT_CHAR) != -1:
                super().error(ErrorType.TYPE_ERROR, f"operator {arguments[0]} applied to two incompatible types")
            else:
                temp_class = self.environment.get_classes(name0)
                if temp_class.find_parent(name1) == None:
                    super().error(ErrorType.TYPE_ERROR, f"operator {arguments[0]} applied to two incompatible types")
                operands[0] = operands[0][0]
        elif isinstance(operands[1], tuple) and isinstance(operands[0], env.Classes):
            name1 = operands[1][1]
            name0 = operands[0].get_name()
            if name1 == super().NULL_DEF or name0 == name1 or operands[0].find_parent(name1) != None:
                operands[1] = operands[1][0]
            elif name0.find(super().TYPE_CONCAT_CHAR) != -1:
                super().error(ErrorType.TYPE_ERROR, f"operator {arguments[0]} applied to two incompatible types")
            else:
                temp_class = self.environment.get_classes(name1)
                if temp_class.find_parent(name0) == None:
                    super().error(ErrorType.TYPE_ERROR, f"operator {arguments[0]} applied to two incompatible types")
                operands[1] = operands[1][0]
        elif isinstance(operands[0], tuple) and isinstance(operands[1], tuple):
            name0 = operands[0][1]
            name1 = operands[1][1]
            if name0 == super().NULL_DEF or name1 == super().NULL_DEF or name0 == name1:
                operands[0] = operands[0][0]
                operands[1] = operands[1][0]
            elif name0.find(super().TYPE_CONCAT_CHAR) != -1 or name1.find(super().TYPE_CONCAT_CHAR) != -1:
                super().error(ErrorType.TYPE_ERROR, f"operator {arguments[0]} applied to two incompatible types")
            else:
                temp_class0 = self.environment.get_classes(name0)
                temp_class1 = self.environment.get_classes(name1)
                if temp_class0.find_parent(name1) == None and temp_class1.find_parent(name0) == None:
                    super().error(ErrorType.TYPE_ERROR, f"operator {arguments[0]} applied to two incompatible types")
                operands[0] = operands[0][0]
                operands[1] = operands[1][0]

        # Compare arguments
        match arguments[0]:
            case "<":
                if type(operands[0]) == int or type(operands[0]) == str:
                    return operands[0] < operands[1]
                super().error(ErrorType.TYPE_ERROR, "invalid operator applied to class")
            case ">":
                if type(operands[0]) == int or type(operands[0]) == str:
                    return operands[0] > operands[1]
                super().error(ErrorType.TYPE_ERROR, "invalid operator applied to class")
            case "<=":
                if type(operands[0]) == int or type(operands[0]) == str:
                    return operands[0] <= operands[1]
                super().error(ErrorType.TYPE_ERROR, "invalid operator applied to class")
            case ">=":
                if type(operands[0]) == int or type(operands[0]) == str:
                    return operands[0] >= operands[1]
                super().error(ErrorType.TYPE_ERROR, "invalid operator applied to class")
            case "==":
                if type(operands[0]) == int  or type(operands[0]) == bool or type(operands[0]) == str or \
                operands[0] == None or isinstance(operands[0], env.Classes):
                    return operands[0] == operands[1]
                super().error(ErrorType.TYPE_ERROR, "invalid operator applied to class")
            case "!=":
                if type(operands[0]) == int  or type(operands[0]) == bool or type(operands[0]) == str or \
                operands[0] == None or isinstance(operands[0], env.Classes):
                    return operands[0] != operands[1]
                super().error(ErrorType.TYPE_ERROR, "invalid operator applied to class")
            case "&":
                if type(operands[0]) == bool:
                    return operands[0] and operands[1]
                super().error(ErrorType.TYPE_ERROR, "invalid operator applied to class")
            case "|":
                if type(operands[0]) == bool:
                    return operands[0] or operands[1]
                super().error(ErrorType.TYPE_ERROR, "invalid operator applied to class")
        return None
    
    # handle unary operator
    # RETURN VALUE: bool value
    def handle_unary(self, arguments, parameters, class_obj, original_class_obj = None):
        # Ensure correct # of arguments called
        if len(arguments) < 2:
            super().error(ErrorType.SYNTAX_ERROR, "invalid number of parameters for operator")
        elif len(arguments) > 2:
            arguments = arguments[0:2]

        operand = arguments[1]
        # Get arguments
        if isinstance(operand, list):
            if operand[0] in env.arithmetic_operators:
                super().error(ErrorType.SYNTAX_ERROR)
            elif operand[0] in env.comparison_operators:
                operand = self.handle_comparison(operand, parameters, class_obj, original_class_obj)
            elif operand[0] == env.UNARY_OPERATOR:
                operand = self.handle_unary(operand, parameters, class_obj, original_class_obj)
            elif operand[0] == super().CALL_DEF:
                operand = self.handle_call(operand[1:], parameters, class_obj, original_class_obj)
            elif operand[0] == super().NEW_DEF:
                operand = self.handle_new(operand[1:])
            else:
                super().error(ErrorType.SYNTAX_ERROR)
            if isinstance(operand, env.ErrorValue):
                return operand
        elif operand in parameters or class_obj.get_field(operand) != None:
            if operand in parameters:
                operand = parameters[operand]
            else:
                operand = class_obj.get_field(operand)
            if operand.get_type() != env.Type.BOOL:
                super().error(ErrorType.SYNTAX_ERROR)
            operand = operand.get_curr_value()
        elif operand == super().TRUE_DEF or operand == super().FALSE_DEF:
            if operand == super().TRUE_DEF:
                operand = True
            else:
                operand = False
        
        if type(operand) != bool:
            super().error(ErrorType.SYNTAX_ERROR)

        if operand:
            return False
        else:
            return True
    
    # set statement
    def handle_set(self, arguments, parameters, class_obj, original_class_obj = None):
        # ensure correct number of arguments passed
        if len(arguments) != 2:
            super().error(ErrorType.SYNTAX_ERROR)
        
        variable = arguments[0]
        new_value = arguments[1]

        # assigns value to new variable
        def assign_variable(self, variable_name, new_value, parameters, class_obj):
            # Find variable
            if isinstance(new_value, tuple):
                new_variable = env.Values(new_value[0], new_value[1])
            else:
                new_variable = env.Values(new_value)
            if variable_name in parameters:
                variable = parameters[variable_name]
            elif class_obj.get_field(variable_name) != None:
                variable = class_obj.get_field(variable_name)
            else:
                self.error(ErrorType.NAME_ERROR, f"unknown variable {variable_name}")

            # Ensure types are same
            if new_variable.get_type() != variable.get_type() and (type(new_variable.get_type()) != str or type(variable.get_type()) != str):
                super().error(ErrorType.TYPE_ERROR, f"type mismatch {new_variable.get_type()} and {variable.get_type()}")
            elif new_variable.get_type() != variable.get_type():
                if new_variable.get_type() != super().NULL_DEF and \
                (new_variable.get_type().find(super().TYPE_CONCAT_CHAR) != -1 or \
                self.environment.get_classes(new_variable.get_type()).find_parent(variable.get_type()) == None):
                    super().error(ErrorType.TYPE_ERROR, f"type mismatch {new_variable.get_type()} and {variable.get_type()}")
                else:
                    new_variable.modify_type(variable.get_type())
            
            # Assign variable
            if variable_name in parameters:
                parameters[variable_name] = new_variable
            elif class_obj.get_field(variable_name) != None:
                class_obj.add_field(new_variable, variable_name)

        # ensure new_value is valid
        if isinstance(new_value, list):
            if new_value[0] in env.arithmetic_operators:
                new_value = self.handle_arithmetic(new_value, parameters, class_obj, original_class_obj)
                if isinstance(new_value, env.ErrorValue):
                    return new_value
                if type(new_value) == str:
                    new_value = "\"" + new_value + "\""
                else:
                    new_value = str(new_value)
            elif new_value[0] in env.comparison_operators:
                new_value = self.handle_comparison(new_value, parameters, class_obj, original_class_obj)
                if isinstance(new_value, env.ErrorValue):
                    return new_value
                new_value = str(new_value).lower()
            elif new_value[0] == env.UNARY_OPERATOR:
                new_value = self.handle_unary(new_value, parameters, class_obj, original_class_obj)
                if isinstance(new_value, env.ErrorValue):
                    return new_value
                new_value = str(new_value).lower()
            elif new_value[0] == super().NEW_DEF:
                new_value = self.handle_new(new_value[1:])
            elif new_value[0] == super().CALL_DEF:
                new_value = self.handle_call(new_value[1:], parameters, class_obj, original_class_obj)
                if isinstance(new_value, env.ErrorValue):
                    return new_value
                if new_value == None:
                    super().error(ErrorType.TYPE_ERROR, f"can't assign to nothing {variable}")
                elif isinstance(new_value, env.Values):
                    new_value = (super().NULL_DEF, new_value.get_type())
                elif type(new_value) == int:
                    new_value = str(new_value)
                elif type(new_value) == str:
                    new_value = "\"" + new_value + "\""
                elif type(new_value) == bool:
                    new_value = str(new_value).lower()
            else:
                super().error(ErrorType.SYNTAX_ERROR)
            assign_variable(self, variable, new_value, parameters, class_obj)
        # new_value is from a constant
        elif new_value == super().TRUE_DEF or new_value == super().FALSE_DEF or new_value == super().NULL_DEF or \
            (new_value.isdigit() or (new_value[0] == "-" and new_value[1:].isdigit())) or (new_value[0] == "\"" and new_value[-1] == "\""):
            assign_variable(self, variable, new_value, parameters, class_obj)
        # new_value is from a parameter or a field
        elif new_value in parameters or class_obj.get_field(new_value) != None:
            if new_value in parameters:
                new_value = parameters[new_value]
            else:
                new_value = class_obj.get_field(new_value)
            if new_value.get_type() == env.Type.UNKNOWN:
                super().error(ErrorType.SYNTAX_ERROR)
            elif new_value.get_type() == env.Type.BOOL:
                new_value = str(new_value.get_curr_value()).lower()
            elif new_value.get_type() == env.Type.INT:
                new_value = str(new_value.get_curr_value())
            elif new_value.get_type() == env.Type.STRING:
                new_value = "\"" + str(new_value.get_curr_value()) + "\""
            elif type(new_value.get_type()) == str:
                new_val = new_value.get_curr_value()
                if new_val == None:
                    new_value = (super().NULL_DEF, new_value.get_type())
                else:
                    new_value = new_val
            assign_variable(self, variable, new_value, parameters, class_obj)
        else:
            super().error(ErrorType.NAME_ERROR, f"invalid field or parameter {new_value}")

        return None
    
    # call statement
    def handle_call(self, arguments, parameters, class_obj, original_class_obj = None):
        # Find class to be referenced
        if arguments[0] == super().ME_DEF:
            class_ptr = class_obj
        elif arguments[0] == super().SUPER_DEF:
            class_ptr = class_obj.get_parent()
        else:
            if isinstance(arguments[0], list):
                if arguments[0][0] == super().NEW_DEF:
                    class_ptr = env.Values(self.handle_new(arguments[0][1:]))
                elif arguments[0][0] == super().CALL_DEF:
                    class_ptr = env.Values(self.handle_call(arguments[0][1:], parameters, class_obj, original_class_obj))
                else:
                    super().error(ErrorType.SYNTAX_ERROR)
                if isinstance(class_ptr, env.ErrorValue):
                    return class_ptr
            elif arguments[0] in parameters:
                class_ptr = parameters[arguments[0]]
            elif class_obj.get_field(arguments[0]) != None:
                class_ptr = class_obj.get_field(arguments[0])
            else:
                super().error(ErrorType.NAME_ERROR, f"invalid field or parameter {arguments[0]}")
            if not isinstance(class_ptr, env.Values):
                super().error(ErrorType.SYNTAX_ERROR)
            class_ptr = class_ptr.get_curr_value()
            if class_ptr == None:
                super().error(ErrorType.FAULT_ERROR, "null dereference")

        # Create list of arguments to pass
        arguments_to_pass = arguments[2:]
        for i in range(len(arguments_to_pass)):
            # new_value is from expression
            if isinstance(arguments_to_pass[i], list):
                if arguments_to_pass[i][0] in env.arithmetic_operators:
                    arguments_to_pass[i] = self.handle_arithmetic(arguments_to_pass[i], parameters, class_obj, original_class_obj)
                    if isinstance(arguments_to_pass[i], env.ErrorValue):
                        return arguments_to_pass[i]
                    if type(arguments_to_pass[i]) == str:
                        arguments_to_pass[i] = "\"" + arguments_to_pass[i] + "\""
                    else:
                        arguments_to_pass[i] = str(arguments_to_pass[i])
                elif arguments_to_pass[i][0] in env.comparison_operators:
                    arguments_to_pass[i] = self.handle_comparison(arguments_to_pass[i], parameters, class_obj, original_class_obj)
                    if isinstance(arguments_to_pass[i], env.ErrorValue):
                        return arguments_to_pass[i]
                    arguments_to_pass[i] = str(arguments_to_pass[i]).lower()
                elif arguments_to_pass[i][0] == env.UNARY_OPERATOR:
                    arguments_to_pass[i] = self.handle_unary(arguments_to_pass[i], parameters, class_obj, original_class_obj)
                    if isinstance(arguments_to_pass[i], env.ErrorValue):
                        return arguments_to_pass[i]
                    arguments_to_pass[i] = str(arguments_to_pass[i]).lower()
                elif arguments_to_pass[i][0] == super().CALL_DEF:
                    arguments_to_pass[i] = self.handle_call(arguments_to_pass[i][1:], parameters, class_obj, original_class_obj)
                    if isinstance(arguments_to_pass[i], env.ErrorValue):
                        return arguments_to_pass[i]
                    if arguments_to_pass[i] == None:
                        super().error(ErrorType.TYPE_ERROR, f"can't assign to nothing {arguments_to_pass[i]}")
                    elif isinstance(arguments_to_pass[i], env.Values):
                        arguments_to_pass[i] = (super().NULL_DEF, arguments_to_pass[i].get_type())
                    elif type(arguments_to_pass[i]) == int:
                        arguments_to_pass[i] = str(arguments_to_pass[i])
                    elif type(arguments_to_pass[i]) == str:
                        arguments_to_pass[i] = "\"" + arguments_to_pass[i] + "\""
                    elif type(arguments_to_pass[i]) == bool:
                        arguments_to_pass[i] = str(arguments_to_pass[i]).lower()
                elif arguments_to_pass[i][0] == super().NEW_DEF:
                    arguments_to_pass[i] = self.handle_new(arguments_to_pass[i][1:])
                else:
                    super().error(ErrorType.SYNTAX_ERROR)

            # new_value is from a constant
            elif arguments_to_pass[i] == super().TRUE_DEF or arguments_to_pass[i] == super().FALSE_DEF or \
                arguments_to_pass[i] == super().NULL_DEF or (arguments_to_pass[i].isdigit() or \
                (arguments_to_pass[i][0] == "-" and arguments_to_pass[i][1:].isdigit())) or \
                (arguments_to_pass[i][0] == "\"" and arguments_to_pass[i][-1] == "\""):
                pass
            # new_value is from a variable
            elif arguments_to_pass[i] in parameters or class_obj.get_field(arguments_to_pass[i]) != None:
                if arguments_to_pass[i] in parameters:
                    arguments_to_pass[i] = parameters[arguments_to_pass[i]]
                else:
                    arguments_to_pass[i] = class_obj.get_field(arguments_to_pass[i])
                if arguments_to_pass[i].get_type() == env.Type.UNKNOWN:
                    super().error(ErrorType.SYNTAX_ERROR)
                elif arguments_to_pass[i].get_type() == env.Type.BOOL:
                    arguments_to_pass[i] = str(arguments_to_pass[i].get_curr_value()).lower()
                elif arguments_to_pass[i].get_type() == env.Type.INT:
                    arguments_to_pass[i] = str(arguments_to_pass[i].get_curr_value())
                elif arguments_to_pass[i].get_type() == env.Type.STRING:
                    arguments_to_pass[i] = "\"" + str(arguments_to_pass[i].get_curr_value()) + "\""
                elif type(arguments_to_pass[i].get_type()) == str:
                    if arguments_to_pass[i].get_curr_value() == None:
                        arguments_to_pass[i] = (super().NULL_DEF, arguments_to_pass[i].get_type())
                    else:
                        arguments_to_pass[i] = arguments_to_pass[i].get_curr_value()
            else:
                super().error(ErrorType.NAME_ERROR, f"invalid field or parameter {arguments_to_pass[i]}")
        
        # Find function to call
        find_method = None
        if original_class_obj != None and arguments[0] != super().SUPER_DEF and not \
        (original_class_obj == None or original_class_obj.find_parent(class_ptr.get_name()) == None):
            find_method = original_class_obj.get_method_from_parent(arguments[1]) 
        if original_class_obj == None or find_method == None:
            find_method = class_ptr.get_method_from_parent(arguments[1]) 
            if original_class_obj == None or original_class_obj.find_parent(class_ptr.get_name()) == None:
                original_class_obj = class_ptr
        if find_method == None:
            super().error(ErrorType.NAME_ERROR, f"unknown method {arguments[1]}")
        function_to_call, class_ptr = find_method

        # call function
        return self.run_function(function_to_call, class_ptr, arguments_to_pass, original_class_obj)

    # Returns a Class object
    def handle_new(self, arguments):
        # ensure valid number of arguments passed
        if len(arguments) < 1:
            super().error(ErrorType.SYNTAX_ERROR)
        arguments = arguments[0]
        class_name = arguments.split(super().TYPE_CONCAT_CHAR)[0]

        # find other class
        other_class = self.environment.get_classes(class_name)
        if other_class == None:
            super().error(ErrorType.TYPE_ERROR, f"No class named {class_name} found")
        elif isinstance(other_class, env.Classes):
            new_object = env.Classes(class_name)
            new_object.copy_from_other_class(other_class)
        else:
            new_object = other_class.create_class(arguments, self)
        return new_object
    
    # handle inputi statement
    def handle_inputi(self, arguments, parameters, class_obj):
        # ensure input is integer
        input = super().get_input()
        if input == None:
            super().error(ErrorType.SYNTAX_ERROR)
        if not input.isdigit() and not (input[0] == '-' and input[1:].isdigit()):
            super().error(ErrorType.SYNTAX_ERROR)

        # ensure valid number of arguments passed
        if len(arguments) < 1:
            super().error(ErrorType.SYNTAX_ERROR)
        else:
            arguments = arguments[0]
        
        # insert input into variable
        new_variable = env.Values(input)
        if arguments in parameters:
            parameter_type = parameters[arguments].get_type() 
            if parameter_type != env.Type.INT:
                super().error(ErrorType.TYPE_ERROR, f"Type mismatch {parameter_type} and int")
            parameters[arguments] = new_variable
        elif class_obj.get_field(arguments):
            field_type = class_obj.get_field(arguments).get_type()
            if field_type != env.Type.INT:
                super().error(ErrorType.TYPE_ERROR, f"Type mismatch {field_type} and int")
            class_obj.add_field(new_variable, arguments)
        else:
            super().error(ErrorType.NAME_ERROR, f"unknown variable {arguments}")

        return None
    
    # handle inputs statement
    def handle_inputs(self, arguments, parameters, class_obj):
        # ensure input exists
        input = super().get_input()
        if input == None:
            super().error(ErrorType.SYNTAX_ERROR)
        input = "\"" + input + "\""

        # ensure valid number of arguments passed
        if len(arguments) < 1:
            super().error(ErrorType.SYNTAX_ERROR)
        else:
            arguments = arguments[0]
        
        # insert input into variable
        new_variable = env.Values(input)
        if arguments in parameters:
            parameter_type = parameters[arguments].get_type() 
            if parameter_type != env.Type.STRING:
                super().error(ErrorType.TYPE_ERROR, f"Type mismatch {parameter_type} and int")
            parameters[arguments] = new_variable
        elif class_obj.get_field(arguments):
            field_type = class_obj.get_field(arguments).get_type()
            if field_type != env.Type.STRING:
                super().error(ErrorType.TYPE_ERROR, f"Type mismatch {field_type} and int")
            class_obj.add_field(new_variable, arguments)
        else:
            super().error(ErrorType.NAME_ERROR, f"unknown variable {arguments}")

        return None
    
    # handle if statement
    def handle_if(self, arguments, parameters, class_obj, original_class_obj = None):
        # ensure valid number of arguments passed
        if len(arguments) < 1:
            super().error(ErrorType.SYNTAX_ERROR)
        elif len(arguments) > 3:
            arguments = arguments[0:3]
        
        # ensure valid condition
        condition = arguments[0]
        if isinstance(condition, list):
            if condition[0] in env.comparison_operators:
                condition = self.handle_comparison(condition, parameters, class_obj, original_class_obj)
            elif condition[0] == env.UNARY_OPERATOR:
                condition = self.handle_unary(condition, parameters, class_obj, original_class_obj)
            elif condition[0] == super().CALL_DEF:
                condition = self.handle_call(condition[1:], parameters, class_obj, original_class_obj)
                if isinstance(condition, env.ErrorValue):
                    return condition
                if type(condition) != bool:
                    super().error(ErrorType.TYPE_ERROR, f"non-boolean if condition {condition}")
            else:
                super().error(ErrorType.TYPE_ERROR, f"non-boolean if condition {condition}")
            if isinstance(condition, env.ErrorValue):
                return condition
        elif condition in parameters or class_obj.get_field(condition) != None:
            if condition in parameters:
                condition = parameters[condition]
            else:
                condition = class_obj.get_field(condition)
            if condition.get_type() != env.Type.BOOL:
                super().error(ErrorType.TYPE_ERROR, f"non-boolean if condition {condition}")
            condition = condition.get_curr_value()
        elif condition == super().TRUE_DEF or condition == super().FALSE_DEF:
            if condition == super().TRUE_DEF:
                condition = True
            else:
                condition = False
        elif condition == super().NULL_DEF or (condition[0] == "\"" and condition[1] == "\"") or \
        (condition.isdigit() or (condition[0] == "-" and condition[1:].isdigit())):
            super().error(ErrorType.TYPE_ERROR, f"non-boolean if condition {condition}")
        else:
            super().error(ErrorType.TYPE_ERROR, f"invalid field or parameter {condition}")

        # determine what to execute
        if condition:
            if len(arguments) < 2:
                return None
            execute = arguments[1]
        else:
            if len(arguments) < 3:
                return None
            execute = arguments[2]
        
        # execute statement
        if (isinstance(execute, list)):
            output = self.run_statement(execute, parameters, class_obj, original_class_obj)
            if execute[0] != super().CALL_DEF:
                return output
            else:
                return None
        else:
            super().error(ErrorType.SYNTAX_ERROR)
    
    # handle while statement:
    def handle_while(self, arguments, parameters, class_obj, original_class_obj = None):
        # ensure valid number of arguments passed
        if len(arguments) < 2:
            super().error(ErrorType.SYNTAX_ERROR)
        elif len(arguments) > 2:
            arguments = arguments[0:2]

        # ensure valid condition
        condition = arguments[0]
        if isinstance(condition, list):
            if condition[0] in env.comparison_operators:
                condition = self.handle_comparison(condition, parameters, class_obj, original_class_obj)
            elif condition[0] == env.UNARY_OPERATOR:
                condition = self.handle_unary(condition, parameters, class_obj, original_class_obj)
            elif condition[0] == super().CALL_DEF:
                condition = self.handle_call(condition[1:], parameters, class_obj, original_class_obj)
                if isinstance(condition, env.ErrorValue):
                    return condition
                if type(condition) != bool:
                    super().error(ErrorType.TYPE_ERROR, f"non-boolean if condition {condition}")
            else:
                super().error(ErrorType.TYPE_ERROR, f"non-boolean if condition {condition}")
            if isinstance(condition, env.ErrorValue):
                return condition
        elif condition in parameters or class_obj.get_field(condition) != None:
            if condition in parameters:
                condition = parameters[condition]
            else:
                condition = class_obj.get_field(condition)
            if condition.get_type() != env.Type.BOOL:
                super().error(ErrorType.TYPE_ERROR, f"non-boolean if condition {condition}")
            condition = condition.get_curr_value()
        elif condition == super().TRUE_DEF or condition == super().FALSE_DEF:
            if condition == super().TRUE_DEF:
                condition = True
            else:
                condition = False
        elif condition == super().NULL_DEF or (condition[0] == "\"" and condition[1] == "\"") or \
        (condition.isdigit() or (condition[0] == "-" and condition[1:].isdigit())):
            super().error(ErrorType.TYPE_ERROR, f"non-boolean if condition {condition}")
        else:
            super().error(ErrorType.TYPE_ERROR, f"invalid field or parameter {condition}")
        
        # execute loop
        statement = arguments[1]
        if condition:
            if (isinstance(statement, list)):
                output = self.run_statement(statement, parameters, class_obj, original_class_obj)
                if isinstance(output, env.ErrorValue):
                    return output
                if statement[0] == super().CALL_DEF:
                    output = None
                if output == None:
                    return self.handle_while(arguments, parameters, class_obj, original_class_obj)
                return output
            else:
                super().error(ErrorType.SYNTAX_ERROR)
        else:
            return None