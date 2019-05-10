def test_multi_excn(snippetcompiler):
    snippetcompiler.setup_for_error(
        """
entity Repo:
    string name
end

entity Host:
    string name
end

entity OS:
    string name
end

Repo.host [1] -- Host
Host.os [1] -- OS

host = Host(name="x")

Repo(host=host,name="epel")

implement Host using std::none
implement Repo using std::none when host.os.name=="os" 
""",
        """Reported 2 errors
error 0:
  The object __config__::Host (instantiated at {dir}/main.cf:17) is not complete: attribute os ({dir}/main.cf:15:6) is not set
error 1:
  Unable to select implementation for entity Repo (reported in __config__::Repo (instantiated at {dir}/main.cf:19) ({dir}/main.cf:19))""",  # noqa: E501
    )
