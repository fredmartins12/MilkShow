"""
MilkShow — Oracle Cloud Instance Creator
Tenta criar a VM A1.Flex gratuita a cada 60s até conseguir.
Uso: python oracle_creator.py
"""
import time
import datetime
import os
import sys


def log(msg, tipo="INFO"):
    hora = datetime.datetime.now().strftime("%H:%M:%S")
    prefixo = {"INFO": "•", "OK": "✓", "ERRO": "✗", "WAIT": "⏳", "WIN": "🎉"}.get(tipo, "•")
    print(f"[{hora}] {prefixo} {msg}", flush=True)


# ── Instala dependências se necessário ───────────────────────
def instalar(pacote):
    import subprocess
    log(f"Instalando {pacote}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", pacote, "-q"])
    log(f"{pacote} instalado com sucesso.", "OK")

log("Verificando dependências...")
try:
    import oci
    log("OCI SDK: OK", "OK")
except ImportError:
    instalar("oci")
    import oci

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
    log("Cryptography: OK", "OK")
except ImportError:
    instalar("cryptography")
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend


# ─────────────────────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────────────────────
CONFIG = {
    "user":        "ocid1.user.oc1..aaaaaaaaijrzgrunszgtz6w3o2z6dzwblaymsctvitcnyjafgwaniy7uh3lq",
    "fingerprint": "ad:86:ea:0c:d1:e9:0d:b8:b8:c9:1f:17:54:94:a8:7a",
    "tenancy":     "ocid1.tenancy.oc1..aaaaaaaakykt7knki655doosl27tdrjqgvjrjvqru6b3ipsbpa4mzhooq4aq",
    "region":      "sa-saopaulo-1",
    "key_file":    r"C:\Users\frede\Downloads\fredericobmartins@gmail.com-2026-04-20T21_35_01.584Z.pem",
}

SUBNET_ID           = "ocid1.subnet.oc1.sa-saopaulo-1.aaaaaaaaohs4cbpl2hrkleek552gegpdqsynipfdhu6xu2mpeo645aaj6jla"
COMPARTMENT_ID      = CONFIG["tenancy"]
AVAILABILITY_DOMAIN = "JMcM:SA-SAOPAULO-1-AD-1"
INSTANCE_NAME       = "milkshow-bot"
SHAPE               = "VM.Standard.A1.Flex"
OCPUS               = 2   # Começa menor p/ ter mais chance — pode ampliar depois gratuitamente
MEMORY_GB           = 12
RETRY_SECONDS       = 30

SSH_PRIV_KEY = r"C:\Users\frede\Downloads\milkshow_ssh.key"
SSH_PUB_KEY  = r"C:\Users\frede\Downloads\milkshow_ssh.pub"


# ─────────────────────────────────────────────────────────────
def gerar_ssh():
    if os.path.exists(SSH_PUB_KEY):
        log(f"Chave SSH já existe: {SSH_PUB_KEY}", "OK")
        with open(SSH_PUB_KEY, "r") as f:
            return f.read().strip()

    log("Gerando par de chaves SSH...")
    priv = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    with open(SSH_PRIV_KEY, "wb") as f:
        f.write(priv.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.OpenSSH,
            serialization.NoEncryption()
        ))
    pub = priv.public_key().public_bytes(
        serialization.Encoding.OpenSSH,
        serialization.PublicFormat.OpenSSH
    ).decode()
    with open(SSH_PUB_KEY, "w") as f:
        f.write(pub)
    log(f"Chave privada salva em: {SSH_PRIV_KEY}", "OK")
    log(f"Chave pública salva em: {SSH_PUB_KEY}", "OK")
    return pub


def get_image_id(compute):
    log("Buscando imagem Ubuntu 24.04 para ARM...")
    try:
        imgs = compute.list_images(
            compartment_id=COMPARTMENT_ID,
            operating_system="Canonical Ubuntu",
            operating_system_version="24.04",
            shape=SHAPE,
            sort_by="TIMECREATED",
            sort_order="DESC"
        ).data
        if not imgs:
            raise Exception("Nenhuma imagem encontrada")
        log(f"Imagem encontrada: {imgs[0].display_name}", "OK")
        return imgs[0].id
    except Exception as e:
        log(f"Erro ao buscar imagem: {e}", "ERRO")
        raise


def main():
    print()
    print("=" * 54)
    print("   MilkShow — Oracle Instance Creator")
    print("   Pressione Ctrl+C para parar")
    print("=" * 54)
    print()

    # ── Valida arquivo PEM ────────────────────────────────────
    log(f"Verificando arquivo PEM: {CONFIG['key_file']}")
    if not os.path.exists(CONFIG["key_file"]):
        log(f"FALHOU — Arquivo PEM não encontrado no caminho:", "ERRO")
        log(f"  {CONFIG['key_file']}", "ERRO")
        log("SOLUÇÃO: Verifique se o arquivo foi baixado em Downloads.", "ERRO")
        input("Pressione Enter para sair...")
        return
    log(f"Arquivo PEM encontrado: OK", "OK")

    # ── Valida conteúdo do PEM ────────────────────────────────
    try:
        with open(CONFIG["key_file"], "r") as f:
            conteudo = f.read()
        if "PRIVATE KEY" not in conteudo:
            log("FALHOU — O arquivo PEM não parece ser uma chave privada válida.", "ERRO")
            log("SOLUÇÃO: Baixe novamente a chave em Oracle → Identity → API Keys.", "ERRO")
            input("Pressione Enter para sair...")
            return
        log("Conteúdo do PEM válido: OK", "OK")
    except Exception as e:
        log(f"FALHOU — Não foi possível ler o arquivo PEM: {e}", "ERRO")
        input("Pressione Enter para sair...")
        return

    log(f"Região: {CONFIG['region']}", "OK")
    log(f"Availability Domain: {AVAILABILITY_DOMAIN}", "OK")
    log(f"Shape: {SHAPE} — {OCPUS} OCPUs / {MEMORY_GB} GB RAM", "OK")
    log(f"Subnet: {SUBNET_ID[:40]}...", "OK")
    print()

    # ── Conecta na Oracle ─────────────────────────────────────
    log("Conectando na Oracle Cloud...")
    try:
        compute = oci.core.ComputeClient(CONFIG)
        network = oci.core.VirtualNetworkClient(CONFIG)
        # Faz uma chamada simples para validar a autenticação
        compute.list_instances(compartment_id=COMPARTMENT_ID, limit=1)
        log("Autenticação Oracle Cloud: OK", "OK")
    except oci.exceptions.ServiceError as e:
        msg = getattr(e, 'message', str(e))
        code = getattr(e, 'code', '')
        log(f"FALHOU — Erro de autenticação (código: {code})", "ERRO")
        log(f"Detalhe: {msg}", "ERRO")
        if "401" in str(e.status) or "NotAuthenticated" in code:
            log("SOLUÇÃO: A API Key pode estar errada ou o fingerprint não confere.", "ERRO")
            log("Verifique em Oracle → Identity → Users → API Keys.", "ERRO")
        elif "404" in str(e.status):
            log("SOLUÇÃO: O OCID do usuário ou tenancy pode estar incorreto.", "ERRO")
        input("Pressione Enter para sair...")
        return
    except Exception as e:
        log(f"FALHOU — Erro inesperado ao conectar: {type(e).__name__}: {e}", "ERRO")
        log("SOLUÇÃO: Verifique sua conexão com a internet.", "ERRO")
        input("Pressione Enter para sair...")
        return

    # ── Busca imagem ──────────────────────────────────────────
    try:
        image_id = get_image_id(compute)
    except oci.exceptions.ServiceError as e:
        log(f"FALHOU — Erro ao buscar imagem Ubuntu: {e.message}", "ERRO")
        input("Pressione Enter para sair...")
        return
    except Exception as e:
        log(f"FALHOU — {type(e).__name__}: {e}", "ERRO")
        input("Pressione Enter para sair...")
        return

    # ── Gera chave SSH ────────────────────────────────────────
    try:
        ssh_pub = gerar_ssh()
    except Exception as e:
        log(f"FALHOU — Erro ao gerar chave SSH: {type(e).__name__}: {e}", "ERRO")
        log("SOLUÇÃO: Verifique se tem permissão de escrita em Downloads.", "ERRO")
        input("Pressione Enter para sair...")
        return

    print()
    log(f"Tudo pronto! Iniciando tentativas a cada {RETRY_SECONDS}s...", "WAIT")
    log("Pode demorar — deixe o terminal aberto. Ctrl+C para parar.", "WAIT")
    print()

    tentativa = 0
    while True:
        tentativa += 1
        log(f"Tentativa {tentativa} — enviando requisição para Oracle...")

        try:
            resp = compute.launch_instance(
                oci.core.models.LaunchInstanceDetails(
                    display_name=INSTANCE_NAME,
                    compartment_id=COMPARTMENT_ID,
                    availability_domain=AVAILABILITY_DOMAIN,
                    shape=SHAPE,
                    shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                        ocpus=float(OCPUS),
                        memory_in_gbs=float(MEMORY_GB)
                    ),
                    source_details=oci.core.models.InstanceSourceViaImageDetails(
                        source_type="image",
                        image_id=image_id,
                        boot_volume_size_in_gbs=50
                    ),
                    create_vnic_details=oci.core.models.CreateVnicDetails(
                        subnet_id=SUBNET_ID,
                        assign_public_ip=True,
                        display_name="milkshow-vnic"
                    ),
                    metadata={"ssh_authorized_keys": ssh_pub}
                )
            )

            inst = resp.data
            print()
            print("=" * 54)
            log("INSTÂNCIA CRIADA COM SUCESSO!", "WIN")
            log(f"ID: {inst.id}", "OK")
            log(f"Estado: {inst.lifecycle_state}", "OK")
            print("=" * 54)

            log("Aguardando IP público (30s)...", "WAIT")
            time.sleep(30)

            try:
                vnics = compute.list_vnic_attachments(
                    compartment_id=COMPARTMENT_ID,
                    instance_id=inst.id
                ).data

                if vnics:
                    vnic = network.get_vnic(vnics[0].vnic_id).data
                    ip = vnic.public_ip
                    print()
                    print("=" * 54)
                    log(f"IP PÚBLICO: {ip}", "WIN")
                    log(f"Comando SSH:", "OK")
                    print(f'    ssh -i "{SSH_PRIV_KEY}" ubuntu@{ip}')
                    print()
                    log("Me manda o IP acima para continuar o deploy!", "WIN")
                    print("=" * 54)
                else:
                    log("VNIC não encontrada ainda — verifique no Console Oracle.", "ERRO")
            except Exception as e:
                log(f"Instância criada mas erro ao buscar IP: {e}", "ERRO")
                log("Verifique o IP no Console Oracle → Compute → Instances", "INFO")

            break

        except oci.exceptions.ServiceError as e:
            msg     = getattr(e, 'message', str(e))
            code    = getattr(e, 'code', '')
            status  = getattr(e, 'status', '')

            if "TooManyRequests" in code or status == 429:
                log(f"ERRO 429 — Muitas requisições. Aguardando 60s para não ser bloqueado...", "WAIT")
                time.sleep(60)
                continue

            elif "Out of capacity" in msg or "InternalError" in code:
                log(f"Sem capacidade no AD-1 de São Paulo. Aguardando {RETRY_SECONDS}s...", "WAIT")

            elif "NotAuthorizedOrNotFound" in code or status == 404:
                log(f"ERRO 404 — Recurso não encontrado ou sem autorização.", "ERRO")
                log(f"Detalhe Oracle: {msg}", "ERRO")
                log("SOLUÇÃO: Verifique se a Subnet ID está correta.", "ERRO")
                log(f"Subnet usada: {SUBNET_ID}", "ERRO")
                break

            elif "NotAuthenticated" in code or status == 401:
                log(f"ERRO 401 — Autenticação falhou.", "ERRO")
                log(f"Detalhe Oracle: {msg}", "ERRO")
                log("SOLUÇÃO: A API Key pode ter expirado. Gere uma nova em Oracle → Identity → API Keys.", "ERRO")
                break

            elif "LimitExceeded" in code or "LimitExceeded" in msg:
                log("ERRO — Limite de recursos atingido.", "ERRO")
                log("SOLUÇÃO: Você já tem instâncias criadas? Verifique em Compute → Instances.", "ERRO")
                log("Se tiver instâncias antigas, delete-as antes de criar uma nova.", "ERRO")
                break

            elif "InvalidParameter" in code or status == 400:
                log(f"ERRO 400 — Parâmetro inválido enviado para a Oracle.", "ERRO")
                log(f"Detalhe Oracle: {msg}", "ERRO")
                log("SOLUÇÃO: Pode ser que o Availability Domain esteja errado.", "ERRO")
                log(f"AD usado: {AVAILABILITY_DOMAIN}", "ERRO")
                break

            else:
                log(f"ERRO inesperado (HTTP {status}, código: {code})", "ERRO")
                log(f"Detalhe Oracle: {msg}", "ERRO")
                log(f"Aguardando {RETRY_SECONDS}s e tentando novamente...", "WAIT")

            time.sleep(RETRY_SECONDS)

        except KeyboardInterrupt:
            print()
            log("Script interrompido pelo usuário.", "INFO")
            break

        except Exception as e:
            log(f"Erro inesperado: {e}", "ERRO")
            log("Aguardando 60s e tentando novamente...", "WAIT")
            time.sleep(RETRY_SECONDS)

    print()
    input("Pressione Enter para fechar...")


if __name__ == "__main__":
    main()
