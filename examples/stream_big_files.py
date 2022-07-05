import uuid
from flask import stream_with_context, Response
from quickbe import WebServer, HttpSession, endpoint, Log

BIG_FILES_FOLDER = '/tmp'


@endpoint(path='download')
def stream_file(session: HttpSession):
    file_name = session.get_parameter('file_name')
    suggested_file_name = f'{uuid.uuid4()}_{file_name}'
    headers = {
        'x-filename': suggested_file_name,
        'X-Suggested-Filename': suggested_file_name,
        'Access-Control-Expose-Headers': 'x-filename',
        'Content-Disposition': f'attachment; filename="{suggested_file_name}"'
    }

    Log.debug(f'Downloading {file_name}')

    def get_file_content():
        with open(f'{BIG_FILES_FOLDER}/{file_name}', 'r') as f:
            for line in f:
                yield line

    return Response(stream_with_context(get_file_content()), mimetype='text/csv', headers=headers)


if __name__ == '__main__':
    WebServer.start(port=888)
