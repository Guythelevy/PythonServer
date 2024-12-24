import api
import argparse
import threading
import socket
import time
import math

cache: dict[tuple[bytes, bool], api.CalculatorHeader] = {}
INDEFINITE = api.CalculatorHeader.MAX_CACHE_CONTROL


def process_request(request: api.CalculatorHeader, server_address: tuple[str, int]) -> tuple[api.CalculatorHeader, int, int, bool, bool, bool]:
    '''
    Function which processes the client request if specified we cache the result
    Returns the response, the time remaining before the server deems the response stale, the time remaining before the client deems the response stale, whether the response returned was from the cache, whether the response was stale, and whether we cached the response
    If the request.cache_control is 0, we don't use the cache and send a new request to the server. (like a reload)
    If the request.cache_control < time() - cache[request].unix_time_stamp, the client doesn't allow us to use the cache and we send a new request to the server.
    If the cache[request].cache_control is 0, the response must not be cached.
    '''
    if not request.is_request:
        raise TypeError("Received a response instead of a request")

    data = request.data
    server_time_remaining = None
    client_time_remaining = None
    was_stale = False
    cached = False
    # Check if the data is in the cache, if the requests cache-control is 0 we must not use the cache and request a new response
    if ((data, request.show_steps) in cache) and (request.cache_control != 0):
        response = cache[(data, request.show_steps)]
        current_time = int(time.time())
        age = current_time - response.unix_time_stamp
        res_cc = response.cache_control if response.cache_control != INDEFINITE else math.inf
        req_cc = request.cache_control if request.cache_control != INDEFINITE else math.inf
        server_time_remaining = res_cc - age
        client_time_remaining = req_cc - age
        # response is still 'fresh' both for the client and the server
        if server_time_remaining > 0 and client_time_remaining > 0:
            return response, server_time_remaining, client_time_remaining, True, False, False
        else:  # response is 'stale'
            was_stale = True

    # Request is not in the cache or the response is 'stale' so we need to send a new request to the server and cache the response
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        try:
            server_socket.connect(server_address)
        except ConnectionRefusedError:
            raise api.CalculatorServerError(
                "Connection refused by server and the request was not in the cache/it was stale")
        server_socket.sendall(request.pack())

        response = server_socket.recv(api.BUFFER_SIZE)

        try:
            response = api.CalculatorHeader.unpack(response)
        except Exception as e:
            raise api.CalculatorClientError(
                f'Error while unpacking request: {e}') from e

        if response.is_request:
            raise TypeError("Received a request instead of a response")

        current_time = int(time.time())
        age = current_time - response.unix_time_stamp
        res_cc = response.cache_control if response.cache_control != INDEFINITE else math.inf
        req_cc = request.cache_control if request.cache_control != INDEFINITE else math.inf
        server_time_remaining = res_cc - age
        client_time_remaining = req_cc - age
        # Cache the response if all sides agree to cache it
        if request.cache_result and response.cache_result and (server_time_remaining > 0 and client_time_remaining > 0):
            cache[(data, request.show_steps)] = response
            cached = True

    return response, server_time_remaining, client_time_remaining, False, was_stale, cached


def proxy(proxy_address: tuple[str, int], server_address: tuple[str, int]) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as proxy_socket:
        proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        proxy_socket.bind(proxy_address)
        proxy_socket.listen(5)
        print(f"Listening on {proxy_address[0]}:{proxy_address[1]}")

        threads = []

        while True:
            try:
                # Accept connection from client
                client_socket, client_address = proxy_socket.accept()  # This accepts the connection from the client

                # Create a new thread to handle the client request
                thread = threading.Thread(target=client_handler, args=(client_socket, client_address, server_address))
                thread.start()
                threads.append(thread)

            except KeyboardInterrupt:
                print("Shutting down...")
                break

        for thread in threads:  # Wait for all threads to finish
            thread.join()



def client_handler(client_socket: socket.socket, client_address: tuple[str, int], server_address: tuple[str, int]) -> None:
    client_prefix = f"{{{client_address[0]}:{client_address[1]}}}"
    
    # רישום חיבור הלקוח לפרוקסי
    print(f"{client_prefix} Connected to proxy")

    # פתיחת חיבור לשרת כאשר הלקוח מתחבר לפרוקסי
    with client_socket, socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        try:
            server_socket.connect(server_address)
            print(f"{client_prefix} Connected to server")
        except ConnectionRefusedError:
            print(f"{client_prefix} Connection to server failed")
            return

        while True:
            # קבלת נתונים מהלקוח
            data = client_socket.recv(api.BUFFER_SIZE)

            if not data:  # אם הלקוח סגר את החיבור
                print(f"{client_prefix} Client disconnected")
                break

            try:
                # ניתוח הבקשה מהלקוח
                request = api.CalculatorHeader.unpack(data)

                # בדיקה אם מדובר בהודעת EXIT
                if request.data == b"EXIT":
                    print(f"{client_prefix} Received EXIT command. Forwarding to server...")
                    server_socket.sendall(data)  # שליחת EXIT לשרת
                    response_data = server_socket.recv(api.BUFFER_SIZE)  # קבלת תגובה מהשרת
                    client_socket.sendall(response_data)  # שליחת תגובה ללקוח
                    print(f"{client_prefix} Closing connection to server after EXIT command")
                    break  # יציאה מהלולאה

                # בדיקת מטמון לפני שליחת הבקשה לשרת
                cache_key = (request.data, request.show_steps)
                if cache_key in cache:
                    response = cache[cache_key]
                    current_time = int(time.time())
                    age = current_time - response.unix_time_stamp
                    res_cc = response.cache_control if response.cache_control != INDEFINITE else math.inf
                    req_cc = request.cache_control if request.cache_control != INDEFINITE else math.inf
                    server_time_remaining = res_cc - age
                    client_time_remaining = req_cc - age

                    if server_time_remaining > 0 and client_time_remaining > 0:
                        print(f"{client_prefix} Cache hit. Returning cached response.")
                        client_socket.sendall(response.pack())
                        continue
                    else:
                        print(f"{client_prefix} Cache stale. Forwarding request to server.")

                # שליחת הבקשה לשרת אם אינה במטמון או פג תוקף
                print(f"{client_prefix} Forwarding request to server")
                server_socket.sendall(data)  # שליחת הבקשה לשרת
                response_data = server_socket.recv(api.BUFFER_SIZE)  # קבלת תגובה מהשרת
                response = api.CalculatorHeader.unpack(response_data)

                # שמירה במטמון אם ניתן
                if request.cache_result and response.cache_result:
                    cache[cache_key] = response
                    print(f"{client_prefix} Response cached")

                # שליחת התגובה ללקוח
                client_socket.sendall(response_data)
                print(f"{client_prefix} Forwarded response to client")

            except Exception as e:
                print(f"{client_prefix} Error: {e}")
                client_socket.sendall(api.CalculatorHeader.from_error(
                    api.CalculatorServerError("Internal proxy error", e),
                    api.CalculatorHeader.STATUS_SERVER_ERROR, False, 0).pack())

        print(f"{client_prefix} Connection closed with client and server")




if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(
        description='A Calculator Server.')

    arg_parser.add_argument('-pp', '--proxy_port', type=int, dest='proxy_port',
                            default=api.DEFAULT_PROXY_PORT, help='The port that the proxy listens on.')
    arg_parser.add_argument('-ph', '--proxy_host', type=str, dest='proxy_host',
                            default=api.DEFAULT_PROXY_HOST, help='The host that the proxy listens on.')
    arg_parser.add_argument('-sp', '--server_port', type=int, dest='server_port',
                            default=api.DEFAULT_SERVER_PORT, help='The port that the server listens on.')
    arg_parser.add_argument('-sh', '--server_host', type=str, dest='server_host',
                            default=api.DEFAULT_SERVER_HOST, help='The host that the server listens on.')

    args = arg_parser.parse_args()

    proxy_host = args.proxy_host
    proxy_port = args.proxy_port
    server_host = args.server_host
    server_port = args.server_port

    proxy((proxy_host, proxy_port), (server_host, server_port))
