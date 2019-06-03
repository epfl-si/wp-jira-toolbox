from imapclient import IMAPClient


if __name__ == "__main__":
    # context manager ensures the session is cleaned up
    with IMAPClient(host="imap.epfl.ch") as client:
        client.use_uid = True
        client.login('jaep@intranet.epfl.ch', 'Aqudadowet2014')
        client.select_folder('Projects/BA/Web@Large/WWP - réponses accred')

        # search criteria are passed in a straightforward way
        # (nesting is supported)
        messages = client.search(['NOT', 'DELETED', 'UNSEEN'])

        # fetch selectors are passed as a simple list of strings.
        response = client.fetch(messages, ['FLAGS', 'RFC822.SIZE', 'BODY[HEADER.FIELDS (FROM)]', 'RFC822'])


        # `response` is keyed by message id and contains parsed,
        # converted response items.
        for message_id, data in response.items():
            print('{id}: {size} bytes, flags={flags}'.format(
                id=message_id,
                size=data[b'RFC822.SIZE'],
                flags=data[b'FLAGS']))