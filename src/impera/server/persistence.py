"""
    Copyright 2015 Impera

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contect: bart@impera.io
"""

from blitzdb.document import Document


class Node(Document):
    """
        A node (a server with a fully qualified name)
    """
    @classmethod
    def create(cls, db, hostname, lastseen):
        return Node(dict(hostname=hostname, lastseen=lastseen, pk=hostname))


class Agent(Document):
    """
        An agent or server
    """
    @classmethod
    def create(cls, db, name, node, role, interval, lastseen):
        return Agent(dict(pk="%s_%s" % (role, name), name=name, node=node, role=role, interval=interval, lastseen=lastseen))


class Fact(Document):
    """
        Facts about a resource
    """
    @classmethod
    def create(cls, db, resource, entity_type, name, value, value_time):
        fact_pk = "%s_%s" % (resource.id, name)
        return Fact(dict(pk=fact_pk, resource=resource, entity_type=entity_type, name=name,
                         value=value, value_time=value_time))


class Resource(Document):
    """
        A resource

        :resource_id impera.resource.Id
    """
    @classmethod
    def create(cls, db, resource_id):
        """
            Create a new resource from the given ID
        """
        try:
            agent = db.get(Agent, {"pk": resource_id.agent_name})
        except Agent.DoesNotExist:
            agent = Agent.create(db, name=resource_id.agent_name, node=None, role=None, interval=None, lastseen=None)
            agent.save(db)

        attributes = dict(
            id=resource_id.resource_str(),
            entity_type=resource_id.entity_type,
            attribute_name=resource_id.attribute,
            attribute_value=resource_id.attribute_value,
            agent=agent,
            pk=resource_id.resource_str()
        )

        return Resource(attributes)


class ResourceVersion(Document):
    """
        A version of a resource

        :resource_id impera.resource.Id
    """
    @classmethod
    def create(cls, db, resource_id, version: int, data):
        try:
            resource = db.get(Resource, {"pk": resource_id.resource_str()})
        except Resource.DoesNotExist:
            resource = Resource.create(db, resource_id)
            resource.save(db)

        return ResourceVersion(dict(
            resource=resource,
            version=version,
            data=data,
            updated=False,
            changes={},
            status="not handled",
            sent=False,
            pk="%s_%s" % (resource.id, version.id)
        ))


class Version(Document):
    """
        A new version of a set of resources
    """
    @classmethod
    def create(cls, db, version_id, date):
        return Version(dict(id=version_id, date=date, pk=version_id, deploy_started=None, deploy_ready=None, dry_run=None))


class Code(Document):
    """
        A new code upload
    """
