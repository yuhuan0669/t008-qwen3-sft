# Readiness correction

The first attempt reached Deployment Ready, then external health returned503. The rollback pod showed the same immediate503 and subsequently recovered to200 with the original spec and aliases. No inference probes ran. The controller treated a single public readiness response as a terminal failure.

The second attempt uses the identical model/template patch. Only the controller now waits up to120 seconds for two consecutive public health200 responses. Persistent failure still rolls back; generation requests are never retried. Offline tests cover503→200→200 and persistent503 timeout. Attempt01 files are preserved.
