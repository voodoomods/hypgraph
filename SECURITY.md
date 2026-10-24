# Security

Please report vulnerabilities privately through GitHub's "Report a vulnerability" (Security tab), not as a public
issue.

What the library promises, and what it doesn't:

- **Tamper evidence, not tamper prevention.** Anyone who can write the SQLite file can change it. `verify()` will
  show that it was changed, unless they rebuild the whole hash chain after their edit. To protect against that,
  publish the head hash somewhere you don't control (a paper, a preregistration, a repository tag). A bundle whose
  head matches the published hash can't have been rewritten since.
- **No authentication.** `author` is whoever the caller says. Hosts that expose the graph (the HTTP server, the MCP
  server, a multi-agent system) must fix the author themselves and refuse the reserved names. `hypgraph serve` binds
  to 127.0.0.1, is read-only by default, and refuses foreign Host headers and cross-origin writes.
- **Scoped bundles are partial.** Events outside the exported investigation are redacted, and their content can't
  be checked. The verifier says so.
