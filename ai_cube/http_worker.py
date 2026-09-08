"""Private cancellable HTTP process. Binary response on stdout, safe errors on stderr."""
import json
import sys
import urllib.request
from .provider import OrcaClient, NoRedirect, ProviderError


def main():
    try:
        item = json.loads(sys.stdin.buffer.read())
        # Caller has validated the configured HTTPS base. An isolated opener also
        # makes the transport usable with loopback fixtures in integration tests.
        client = OrcaClient(item['key'], timeout=item['timeout'],
                            opener=urllib.request.build_opener(NoRedirect()).open)
        client.base = item['url']
        data = client._post('', item['payload'], item['limit'])
        sys.stdout.buffer.write(data)
        return 0
    except ProviderError as exc:
        sys.stderr.write(str(exc))
    except Exception:
        sys.stderr.write('OrcaRouter request worker failed')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
