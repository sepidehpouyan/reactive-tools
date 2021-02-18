# Add support for a new architecture

In this tutorial, we will describe all the steps to do to add support for a new architecture.

## Preliminary notes

- **You MUST NOT modify** any existing files except for `modules/__init__.py` and `nodes/__init__.py`
  - Your new architecture will be managed automatically
  
- If you need to install some python libraries through `pip`, add the name in the `install_requires` list in `setup.py` (line 16)
  - Please declare a specific version! This way we don't risk that future updates break the app
  
- If you have some other external python libraries (e.g., the sancus python library), you need to add the path in your PYTHONPATH environment variable in order to use them
  - Example: `  PYTHONPATH=$PYTHONPATH:/usr/local/share/sancus-compiler/python/lib/`
  - If this is the case, **DO NOT** import a module at the beginning of your files, otherwise people that do not have such module would not be able to run the application. Instead, import the module inside the functions where you use it
    - Example: `modules/sancus.py` at line 207

## High-level view of the steps to do

- Fork this repository in your account
- [optional] create a new branch, where you will implement your code
- Implement & test code
- Open a Pull Request (PR) from your branch to the `main` branch of **this** repository (not the one you forked!)
- Wait for a review and, optionally, improve code
- Update your code according to the review received
- End: your code is merged to the main repo!

## Implementation

In this tutorial we will describe how to add support for the `TrustZone` architecture.

### Add rules

A rule file is a YAML file which contains some logical constraints about the definition of the deployment descriptor (nodes, modules, connections). Essentially, the purpose of these rules is to ensure that the deployment descriptor is structured as expected, and to give a meaningful error if something is wrong. 

- All the rule files are stored in the `rules` folder.

- Examples of rules: 
  - *each item in the `nodes` section of the deployment descriptor must provide a type, a name, an IP address and a port.* 
  - *a port must be a positive 16-bit integer*
- In `rules/default`, pre-defined rules are stored. For modules and nodes, we wrote some generic rules that all the types of nodes/modules should follow (e.g., for nodes, like in the example above)
- In `rules/modules` and `rules/nodes` specific rules for specific architectures are stored (e.g., Sancus, SGX, etc..)

**Your task**

- **[required]** Create an empty `trustzone.yaml` file both in `rules/modules` and `rules/nodes`
- [optional] Fill the files with your rules. These will be evaluated automatically at runtime.
  - It's optional, but **recommended**
  - Each rule is a key-value pair where the key is a string message that will be printed if the rule is not satisfied, and the value is your logical expression in **python code**
    - To satisfy the rule, the expression must be evaluated to `True`
    - Some helper functions are provided in `rules/evaluators.py`, which can be used
    - Check the other rule files to get an idea of how to declare these rules

### Add Node and Module classes

- **[required]** add a file called `trustzone.py` in the folder `nodes`
  - This file has to declare a new class called `TrustZoneNode`, which extends the base class `Node`
- **[required]** add a file called `trustzone.py` in the folder `modules`
  - This file has to declare a new class called `TrustZoneModule`, which extends the base class `Module`

These classes have to implement **at least** the abstract methods of the corresponding base classes, according to the description provided in the `base.py` files
- For some methods, a default implementation is provided. If needed, you can override these methods in the subclasses
- In the `__init__` function of your classes, **you must**  call `super().__init__(args)` , where args are the parameters of the `__init__` function in the base class (again, look at the `base.py`)

### Update `__init__.py` files in `nodes/` and `modules/`

To have your classes used by the application, you should modify these two files:

- `nodes/__init__.py` 
- `modules/__init__.py`

For both the files, the procedure is the same and very intuitive.

- The examples below show how to update `modules/__init__.py`. For the same file under `nodes`, the procedure is analogous (just replace`module` with `node`)

**[required] Import your classes** 

```python
from .trustzone import TrustZoneModule
```

**[required] Declare your rules files**

You should update the `module_rules`  and `node_rules` dicts as described below

- **NOTE:** the key `"trustzone"` is the type of your node/module as written in the deployment descriptor

```python
module_rules = {
    # ...
	
    # THIS is what you have to add:
    "trustzone" : "trustzone.yaml"
}
```

The application will automatically fetch the `trustzone.yaml` file inside the `rules/nodes` or `rules/modules` folders.

**[required] Declare your load function**

The `load` function, declared as an abstract static method in the base class, takes as input the definition of the node/module as written in the deployment descriptor and creates the `TrustZoneNode` or `TrustZoneModule` object.

- The `dump` function, instead, does the opposite work

You should update the `module_funcs` and `node_funcs` as described below

- **NOTE:** the key `"trustzone"` is the type of your node/module as written in the deployment descriptor

```python
module_funcs = {
    # ...
	
    # THIS is what you have to add:
    "trustzone" : TrustZoneModule.load
}
```

**[optional] cleanup coroutines**

If your `Node` or `Module` classes need to perform certain operations before the application ends (e.g., kill some background process), you can add an entry in the `module_cleanup_coros` and `node_cleanup_coros` lists.

- This is not required, but it is **recommended** to update these lists even if you do not have any task to do.
- The `cleanup` method of your classes has a default implementation in the base class, therefore you do not have to implement new methods by yourself if you don't need to do any cleanup operations.

```python
module_cleanup_coros = [
    # ...
	
    # THIS is what you have to add:
	TrustZoneModule.cleanup
]
```

### Implement methods

Now, you just have to implement all the abstract methods in your classes inherited from the base classes `Node` and `Module`. 

- Check the `base.py` file for a description of the methods you have to override
- Check other implementations (e.g., `sancus.py`) for some additional hints
- You can of course implement new methods if needed, as well as override default implementation of methods in the base class