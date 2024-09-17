"""
    Copyright 2021 Inmanta

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: code@inmanta.com
"""

from inmanta import compiler


def test_2787_function_rescheduling(snippetcompiler):
    """
    Particular case where a bug in handling of plugin calls causes cycle breaking to fail
    """
    snippetcompiler.setup_for_snippet(
        """

   import tests

   entity Rule:
     bool purged
   end

   entity Service:
     string name
   end

   Rule.services [0:] -- Service

   Service.effective_services [0:] -- Service
   Service.subservice [0:] -- Service
   implementation effective_members for Service:
        for service in subservice:
            self.effective_services += service.effective_services
        end
   end

   a = Rule(
        services = Service( name="top",
            subservice=Service(name="inner")
        ),
        purged = tests::resolve_rule_purged_status(a.services)
  )

  implementation rq for Rule:
    if self.purged:
       self.requires = services
    else:
       self.provides = services
    end
  end

  implement Rule using rq
  implement Service using effective_members
    """
    )

    compiler.do_compile()


def test_function_rescheduling_with_side_effect(snippetcompiler):
    """
    This would cause an infinite loop because:

    std::key_sort([Child()], "name")

    is evaluated as a single expression the name="x" is evaluated separately.
    This means that when executing this statement:

    - a child is constructed  , name="x" is emitted
    - list is constructed
    - key_sort is called
    - key_sort raises exception because it can't find name , statement is queued, waiting for name
    - name="x" is called
    - statement is rescheduled, back to 1 (which constructs a new child)
    """

    snippetcompiler.setup_for_snippet(
        """entity Test:

        end

        entity Child:
            string name
        end

        Test.child [0:] -- Child

        Test(
            child=std::key_sort([Child(name="x")], "name")
        )

        implement Child using std::none
        implement Test using std::none
        """,
        autostd=True,
    )
    compiler.do_compile()


def test_function_rescheduling_plugin_with_context(snippetcompiler):
    """Ensure that when a plugin is rescheduled, context injection doesn't break"""

    snippetcompiler.setup_for_snippet(
        """
        import tests
        std::print(tests::context_tester(container))


        entity Container:
        end



        container = Container()
        for i in std::sequence(6):
            container.requires += Container()
        end

        implement Container using std::none

        """,
        autostd=True,
    )
    compiler.do_compile()
