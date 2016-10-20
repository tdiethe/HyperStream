# The MIT License (MIT) # Copyright (c) 2014-2017 University of Bristol
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#  DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
#  OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
#  OR OTHER DEALINGS IN THE SOFTWARE.
"""
Plate and plate manager definitions.
"""
from ..utils import Printable, MetaDataTree, PlateEmptyError, PlateDefinitionError
from ..models import PlateDefinitionModel

import logging
from mongoengine.context_managers import switch_db
from mongoengine import DoesNotExist, MultipleObjectsReturned


class Plate(Printable):
    """
    A plate in the execution graph. This can be thought of as a "for loop" over the streams in a node
    """
    def __init__(self, plate_id, meta_data_id, values, parent_plate=None):
        """
        Initialise the plate
        :param plate_id: Plate ID
        :param meta_data_id: Meta data ID - corresponds to the tag in the meta data definitions
        :param values: The plate values - corresponds to the data in the meta data definitions
        :param parent_plate: The parent plate (object reference)
        :type parent_plate: Plate
        """
        self.plate_id = plate_id
        self.meta_data_id = meta_data_id

        self.values = []
        self.cardinality = 0
        for pv in values:
            self.values.append(tuple(sorted(pv.items())))
            if self.cardinality == 0:
                self.cardinality = len(pv)
            else:
                if len(pv) != self.cardinality:
                    raise ValueError("Plate values have inconsistent cardinality")

        self.values = [tuple(sorted(pv.items())) for pv in values]
        self.parent = parent_plate

    def _get_ancestors(self, current=None):
        if not current:
            current = []
        current.insert(0, self.plate_id)
        if self.is_root:
            if current:
                return current
        else:
            return self.parent._get_ancestors(current)

    @property
    def ancestors(self):
        return self._get_ancestors()

    @property
    def is_root(self):
        return self.parent is None


class PlateManager(Printable):
    """
    Plate manager. Manages the mapping between plates defined in the database with the global meta data definition.
    """
    def __init__(self, global_meta_data):
        """
        Initialise the manager

        Want to get meta-data dictionaries for all plate combinations
        e.g.

        H plate, want

        {'H': [
          {'house': '1'},
          {'house': '2'}
        ]}

        H1 plate, want

        {'H1': [{'house': '1'}]}

        H.R plate, want

        {'H.R': [
          {'house': '1', 'resident': '1'},
          {'house': '1': 'resident': '2'},
          {'house': '2': 'resident': '1'}
        }

        :param global_meta_data: The global meta data, which will be stored in a tree structure
        """
        self.plates = {}

        self.global_plate_definitions = MetaDataTree()

        # Populate the global plate definitions from dict given in the config file
        for item in global_meta_data:
            self.global_plate_definitions.create_node(**item)

        logging.info("Global plate definitions: ")
        logging.info(self.global_plate_definitions)

        # Plate definitions (arrays of streams)
        with switch_db(PlateDefinitionModel, db_alias="hyperstream"):
            for p in PlateDefinitionModel.objects:
                self.add_plate(p)

    def create_plate(self, plate_id, description, meta_data_id, values, complement, parent_plate):
        """
        Create a new plate, and commit it to the database
        :param plate_id: The plate id - required to be unique
        :param description: A human readable description
        :param meta_data_id: The meta data id, which should correspond to the tag in the global meta data
        :param values: Either a list of string values, or the empty list (for use with complement)
        :param complement: If complement is true, then the complement of the values list will be used when getting
        values from the global meta data
        :param parent_plate: The parent plate identifier
        :return: The newly created plate
        :type plate_id: str | unicode
        :type complement: bool
        :type values: list | tuple
        """
        # Make sure the plate id doesn't already exist
        with switch_db(PlateDefinitionModel, db_alias='hyperstream'):
            try:
                p = PlateDefinitionModel.objects.get(plate_id=plate_id)
                if p:
                    logging.info("Plate with id {} already exists".format(plate_id))
                    return self.plates[plate_id]
            except DoesNotExist:
                pass
            except MultipleObjectsReturned:
                raise

            plate_definition = PlateDefinitionModel(
                plate_id=plate_id,
                description=description,
                meta_data_id=meta_data_id,
                values=values,
                complement=complement,
                parent_plate=parent_plate
            )

            self.add_plate(plate_definition)
            plate_definition.save()
            return self.plates[plate_id]

    def add_plate(self, plate_definition):
        """
        Add a plate using the plate definition
        :param plate_definition: The plate definition
        :return: None
        :type plate_definition: PlateDefinitionModel
        """
        values = self.get_plate_values(plate_definition)

        # TODO: We should also be checking that the plate is defined over all of the values of the parent plate
        self.plates[plate_definition.plate_id] = Plate(
            plate_id=plate_definition.plate_id,
            meta_data_id=plate_definition.meta_data_id,
            values=values,
            parent_plate=self.plates[plate_definition.parent_plate] if plate_definition.parent_plate else None)

        logging.debug("Added plate: {}".format(self.plates[plate_definition.plate_id]))

    def get_plate_values(self, plate_definition):
        """
        Gets the plate values from the global meta data according to the given plate definition
        :param plate_definition: The plate definition
        :return: The plate values
        :type plate_definition: PlateDefinitionModel
        """
        if not plate_definition.values and not plate_definition.complement:
            raise PlateDefinitionError()

        values = []
        for n in self.global_plate_definitions.all_nodes():
            if n.tag == plate_definition.meta_data_id:
                if not plate_definition.values or n.data in plate_definition.values:
                    if plate_definition.parent_plate:
                        # This plate has parent plates, so we need to get parent data for the node
                        parent_plate_value = self.get_parent_plate_value(self.global_plate_definitions, n)
                        if tuple(parent_plate_value) not in self.plates[plate_definition.parent_plate].values:
                            continue
                        values.insert(0, self.get_parent_data(self.global_plate_definitions, n, {n.tag: n.data}))
                    else:
                        values.insert(0, {n.tag: n.data})
        if not values:
            raise PlateEmptyError(plate_definition.plate_id)
        return values

    def get_parent_plate_value(self, tree, node, value=None):
        """
        Recurse up the tree getting parent plate values
        :param tree: The tree
        :param node: The current node
        :param value: The initial plate value
        :return: The plate value as a list of tuples
        """
        if value is None:
            value = []
        parent = tree.parent(node.identifier)
        if parent.is_root():
            # value.append((parent.tag, parent.identifier))
            return value
        value = self.get_parent_plate_value(tree, parent, value)
        if "." in parent.identifier:
            pass
        value.append((parent.tag, parent.data))
        return value

    @staticmethod
    def get_parent_data(tree, node, d):
        """
        Recurse up the tree getting parent data
        :param tree: The tree
        :param node: The current node
        :param d: The initial dictionary
        :return: The hierarchical dictionary
        """
        parent = tree.parent(node.identifier)
        if parent.is_root():
            return d
        d[parent.tag] = parent.data
        return PlateManager.get_parent_data(tree, parent, d)
