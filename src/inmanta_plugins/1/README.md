This package exists, because Python doesn't allow you to create an empty native namespace package. The name of this package is
`1`, because `1` isn't a valid identifier in the Inmanta language. As such, `import 1` will always result in a compilation
error.
