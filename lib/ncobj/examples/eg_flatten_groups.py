"""
Examples demonstrating how to 'flatten' datasets with sub-groups :
Copy all input variables to top level, and rename to avoid any conflicts.

"""
from ncobj import Group
from ncobj.grouping import all_variables, complete, group_path


def flat_prefix_all(grp: Group) -> Group:
    result = Group()
    for var in all_variables(grp):
        # Get the name prefixed by containing groups (before detaching).
        var_pathname = group_path(var)
        # Take a detached copy, so rename won't upset anything else.
        var = var.detached_copy() # So we can rename it
        # Rename, prefixing name of containing groups.
        var.rename(var_pathname)
        result.variables.add(var)

    # Complete the result : this adds in all the necessary dimensions.
    complete(result)
    return result

def flat_prefix_whereneeded(grp: Group) -> Group:
    vars_by_name = {}
    for var in all_variables(grp):
        # Collect all variables, arranged by name.
        var_name = var.name
        vars_with_name = vars_by_name.setdefault(var_name, [])
        vars_with_name.append(var)

    result = Group()
    for var_name, vars in vars_by_name.items():
        # If there is any name collision, rename to disambiguate.
        if len(vars) > 1:
            renamed_vars = []
            for var in vars:
                # Get the name prefixed by containing groups (before detaching).
                var_pathname = group_path(var)
                var = var.detached_copy()
                var.rename(var_pathname)
                renamed_vars.append(var)
            vars = renamed_vars
        # Add all these vars to the output
        for var in vars:
            result.variables.add(var.detached_copy())

    # Complete the result : this adds in all the necessary dimensions.
    complete(result)
    return result
