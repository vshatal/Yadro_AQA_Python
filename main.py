import xml.etree.ElementTree as ET
import json


input_path = "input/test_input.xml"
config_path = "out/config.xml"
meta_path = "out/meta.json"


class Class:
    def __init__(self, name: str, is_root: bool, documentation: str):
        self.name = name
        self.is_root = is_root
        self.documentation = documentation
        self.min_ = "0"
        self.max_ = "0"
        self.attributes = []
        self.children = []

    def add_attribute(self, name: str, type_: str) -> None:
        self.attributes.append({"name": name,
                                "type": type_
                                })

    def add_child(self, source: str) -> None:
        self.children.append(source)

    def add_minmax(self, min_: str, max_: str) -> None:
        self.min_ = min_
        self.max_ = max_


class ClassBuilder:
    @staticmethod
    def minmax_from_multiplicity(mult: str) -> (str, str):
        if ".." in mult:
            min_mult, max_mult = mult.split("..")
        else:
            min_mult, max_mult = mult, mult
        return min_mult, max_mult

    def __init__(self, xml_file: str):
        self.tree = ET.parse(xml_file)
        self.root = self.tree.getroot()
        self.classes = {}
        self.aggregations = []

    def build(self) -> None:
        self.init_classes()
        self.init_children()
        self.init_minmax()

    def get_classes(self) -> dict:
        return self.classes

    def init_classes(self) -> None:
        for cl in self.root.findall("Class"):
            name = cl.get("name")
            is_root = cl.get("isRoot") == "true"
            document = cl.get("documentation")
            class_ = Class(name, is_root, document)

            for at in cl.findall("Attribute"):
                at_name = at.get("name")
                at_type = at.get("type")
                class_.add_attribute(at_name, at_type)

            self.classes[cl.get("name")] = class_

    def init_children(self) -> None:
        for ag in self.root.findall("Aggregation"):
            class_ = self.classes[ag.get("target")]
            source = ag.get("source")
            class_.add_child(source)

    def init_minmax(self) -> None:
        targets = []
        sources = []

        for ag in self.root.findall("Aggregation"):
            targets.append(ag.get("target"))
            sources.append(ag.get("source"))

        for name, cl in self.classes.items():
            mult = "0"
            if name in targets:
                aggregation = self.root.find(f"./Aggregation[@target='{name}']")
                mult = aggregation.get("targetMultiplicity")
            elif name in sources:
                aggregation = self.root.find(f"./Aggregation[@source='{name}']")
                mult = aggregation.get("sourceMultiplicity")
            min_, max_ = self.minmax_from_multiplicity(mult)
            cl.add_minmax(min_, max_)


class ConfigMaker:
    @staticmethod
    def find_main_root(classes: dict) -> Class:
        main_root = None
        for cl in classes.values():
            if cl.is_root:
                main_root = cl
        return main_root

    @staticmethod
    def make_config(classes: dict) -> ET:
        main_root = ConfigMaker.find_main_root(classes)
        root = ET.Element(main_root.name)
        ConfigMaker.make_branch(root, main_root)
        return root

    @staticmethod
    def make_branch(root: ET.Element, class_: Class) -> None:
        for attribute in class_.attributes:
            element = ET.SubElement(root, attribute['name'])
            element.text = attribute['type']

        for child in class_.children:
            element = ET.SubElement(root, classes[child].name)
            ConfigMaker.make_branch(element, classes[child])


class JsonMaker:
    @staticmethod
    def make_json(classes: dict) -> list:
        json_list = []
        for class_ in classes.values():
            cl_dict = {"class": class_.name,
                       "documentation": class_.documentation,
                       "isRoot": class_.is_root,
                       }
            if not class_.is_root:
                cl_dict["max"] = class_.max_
                cl_dict["min"] = class_.min_
            cl_dict["parameters"] = []

            for attr in class_.attributes:
                cl_dict["parameters"].append({"name": attr["name"],
                                              "type": attr["type"]
                                              })
            for child in class_.children:
                cl_dict["parameters"].append({"name": child,
                                              "type": "class"
                                              })
            json_list.append(cl_dict)
        return json_list


builder = ClassBuilder(input_path)
builder.build()
classes = builder.get_classes()

tree = ET.ElementTree(ConfigMaker.make_config(classes))
ET.indent(tree, space='    ')
tree.write(config_path)

json_list = JsonMaker.make_json(classes)
with open(meta_path, 'w') as f:
    json.dump(json_list, f, indent=4)
