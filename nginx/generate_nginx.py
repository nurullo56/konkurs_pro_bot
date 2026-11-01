def generate_nginx_conf(domain, num_bots, start_port=8001):
    conf = f"""server {{
    listen 80;
    server_name {domain};

    # Xavfsizlik uchun SSL/HTTPS ulanishi tavsiya etiladi
    # listen 443 ssl;
    # ssl_certificate /path/to/fullchain.pem;
    # ssl_certificate_key /path/to/privkey.pem;

"""
    for i in range(1, num_bots + 1):
        port = start_port + i - 1
        conf += f"""    # {i}-Bot (Port: {port})
    location ^~ /webhook/bot{i} {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $http_host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
    }}

"""
    
    conf += "}\n"
    return conf

if __name__ == "__main__":
    domain = "smart-tools.uk"
    num_bots = 65
    
    with open("C:/Users/Acer/Downloads/konkurs_bot_pro/nginx/default.conf", "w", encoding="utf-8") as f:
        f.write(generate_nginx_conf(domain, num_bots))
    
    print("Nginx configuration successfully generated!")
