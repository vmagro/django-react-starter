from urllib.request import urlopen
import json

import graphql
from graphql.parser import GraphQLParser


class Query(object):
    """Parse and execute graphql queries."""

    def __init__(self, query):
        """Create a new Query object from a query string or AST."""
        parser = GraphQLParser()
        if type(query) == str:
            # TODO(vmagro) this probably needs to change if we support mutations
            self.ast = parser.parse(query).definitions[0]
        elif type(query) == graphql.ast.Query:
            self.ast = query
        else:
            raise TypeError('query must be a str or graphql.ast.Query')

    def execute(self, ast=None):
        """Execute the query by calling the normal REST api."""
        query = self.ast
        if ast is not None:
            query = ast
        # the top level selections are things that we need to make REST calls for
        selections = query.selections
        response = {}
        for field in selections:
            url = 'http://localhost:8000/api/' + field.name
            if field.arguments:
                # assume that an argument 'id' is included in the url
                id_arg = [a for a in field.arguments if a.name == 'id']
                if id_arg:
                    url += f'/{id_arg[0].value}'
                other_args = [a for a in field.arguments if a.name != 'id']
                if other_args:
                    url += '?'
                    for arg in other_args:
                        url += f'&{arg.name}={arg.value}'
            # TODO(vmagro) support pagination on list views
            body = json.loads(urlopen(url).read())

            if 'results' in body:
                # return a list
                data = [self.execute_on_dict(field, item) for item in body['results']]
            else:
                # returning just one object
                data = self.execute_on_dict(field, body)
            response[field.name] = data

        return {'data': response}

    def strip_dict(self, ast, d):
        """Strip a dict so that it only has fields that were requested in the query."""
        new = {}
        for field in ast.selections:
            if field.selections:
                new[field.name] = self.strip_dict(field, d[field.name])
            else:
                new[field.name] = d[field.name]
        return new

    def execute_on_dict(self, ast, d):
        """Run a query AST on a dictionary that came from the API server."""
        for field in ast.selections:
            # if there are nested selections, we might need to make another query
            if field.selections:
                # first check if we have the data requested already
                # we don't need to do anything for this field if we already have the data
                if field.name not in d:
                    print(f'{field} not in dict at all, can\'t proceed')
                    raise KeyError(f'{field} not in API response')
                if type(d[field.name]) is not dict:
                    print(f'{field} is a URL, retrieving its data')
                    # if the field isn't in the dictionary, we have to make a new query
                    # the field must be a url if it's not the actual data we want
                    body = urlopen(d[field.name]).read()
                    result = json.loads(body)
                    d[field.name] = self.execute_on_dict(field, result)
        return self.strip_dict(ast, d)
