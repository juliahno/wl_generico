#!/usr/bin/python

# Script para download e criacao de estrutura generica de JVMs,
# incluindo templates, clusters, datasources, startup classes e
# deploys. 

# Para o correto funcionamento deste script, os arquivos "hosts",
# "pacotes" e "properties" devem acompanha-lo.

# MELHORIAS: 
# - METODO CRIA_MACHINE
# - CONTROLE DE ERROS (REQUESTS)
# - CONTROLE DE VERSOES (GIT)
# - VERIFICACAO DA EXISTENCIA DE ARQUIVOS REMOTOS
# - TRATAMENTO DE ARQUIVOS TGZ (DESCOMPACTACAO)

import requests
import getpass
import json
import os

###############################################################################################################################

def cria_datasource():
  nome_jdbc_resource = nome_datasource = propriedades['datasource']['name']
  nome_jdbc_jndi = propriedades['datasource']['jndi_names']
  driver_name = propriedades['datasource']['driver']
  driver_url = propriedades['datasource']['url']
  test_table = propriedades['datasource']['test_table']
  jdbc_targets = [ 'cluster-cfe-ace', 'cluster-cfe-acesso', 'cluster-cfe-sgw' ]

  print("- CRIANDO DATASOURCE...")
  
  dados_jdbc = {
    'name': nome_datasource
  }

  dados_jdbc_resource = {
    'name': nome_jdbc_resource
  }

  dados_jdbc_jndi = {
    'JNDINames': nome_jdbc_jndi
  }

  dados_jdbc_driver = {
    'driverName': driver_name,
    'url': driver_url,
    'password': senha_datasource
  }

  dados_jdbc_poolparams = {
    'testTableName': test_table
  }

  dados_jdbc_targets = {
    'targets': []
  }

  resposta_coletaClusters = requests.get(url_console + endpoint_coletaClusters, headers = header, auth = (usuario, senha))
  relacao_clusters = []
  for cluster in resposta_coletaClusters.json()['items']:
    relacao_clusters.append(cluster['identity'][1])

  for item in jdbc_targets:
    if (item in relacao_clusters):
      dados_jdbc_targets['targets'].append({ 'identity': [ 'clusters', item ] })

  endpoint_jdbc = "/management/weblogic/latest/edit/JDBCSystemResources"
  endpoint_jdbc_resource = "/management/weblogic/latest/edit/JDBCSystemResources/" + nome_datasource + "/JDBCResource"
  endpoint_jdbc_jndi = "/management/weblogic/latest/edit/JDBCSystemResources/" + nome_datasource + "/JDBCResource/JDBCDataSourceParams"
  endpoint_jdbc_driver = "/management/weblogic/latest/edit/JDBCSystemResources/" + nome_datasource + "/JDBCResource/JDBCDriverParams"
  endpoint_jdbc_poolparams = "/management/weblogic/latest/edit/JDBCSystemResources/" + nome_datasource + "/JDBCResource/JDBCConnectionPoolParams"
  endpoint_jdbc_properties = "/management/weblogic/latest/edit/JDBCSystemResources/" + nome_datasource + "/JDBCResource/JDBCDriverParams/properties/properties"
  endpoint_jdbc_targets = "/management/weblogic/latest/edit/JDBCSystemResources/" + nome_datasource

  resposta_jdbc = requests.post(url_console + endpoint_jdbc, json=dados_jdbc, headers = header, auth = (usuario, senha))
  resposta_jdbc_resource = requests.post(url_console + endpoint_jdbc_resource, json=dados_jdbc_resource, headers = header, auth = (usuario, senha))
  resposta_jdbc_jndi = requests.post(url_console + endpoint_jdbc_jndi, json=dados_jdbc_jndi, headers = header, auth = (usuario, senha))
  resposta_jdbc_driver = requests.post(url_console + endpoint_jdbc_driver, json=dados_jdbc_driver, headers = header, auth = (usuario, senha))
  resposta_jdbc_poolparams = requests.post(url_console + endpoint_jdbc_poolparams, json=dados_jdbc_poolparams, headers = header, auth = (usuario, senha))

  for chave, valor in propriedades['datasource']['properties'].items():
    dados_jdbc_properties = {
      'name': chave,
      'value': valor
    }
    resposta_jdbc_properties = requests.post(url_console + endpoint_jdbc_properties, json=dados_jdbc_properties, headers = header, auth = (usuario, senha))
  
  resposta_jdbc_targets = requests.post(url_console + endpoint_jdbc_targets, json=dados_jdbc_targets, headers = header, auth = (usuario, senha))

#------------------------------------------------------------------------------------------------------------------------------

def cria_startupclasses():
  startupclass_nome = propriedades['startupclasses']['nome']
  startupclass_classname = propriedades['startupclasses']['className']
  
  dados_startupclasses = {
    'name': startupclass_nome,
    'type': 'StartupClass',
    'className': startupclass_classname,
    'loadBeforeAppDeployments': True,
    'failureIsFatal': True,
    'loadBeforeAppActivation': True,
    'deploymentOrder': 1, 
    'targets': []
  }
  
  endpoint_startupclasses = "/management/weblogic/latest/edit/startupClasses/"
  # endpoint_startupclasses_update = "/management/weblogic/latest/edit/startupClasses/" + startupclass_nome

  resposta = requests.get(url_console + endpoint_coletaClusters, headers = header, auth = (usuario, senha))

  for item in resposta.json()['items']:
    dados_startupclasses['targets'].append({ 'identity': item['identity'] })

  print("- CRIANDO STARTUP CLASSES...")
  resposta_startupclasses = requests.post(url_console + endpoint_startupclasses, json=dados_startupclasses, headers = header, auth = (usuario, senha))
  
  # if (resposta_startupclasses.status_code == 404):
  #   resposta_startupclasses = requests.post(url_console + endpoint_startupclasses_update, json=dados_startupclasses, headers = header, auth = (usuario, senha))

#------------------------------------------------------------------------------------------------------------------------------

def baixa_pacote(diretorio_pacote, ip_console, nome_pacote_war):
    usuario_atf = raw_input("USUARIO (ATF): ")
    senha_atf = getpass.getpass("SENHA (ATF): ")

    url_consulta_atf = "http://atf.intranet.bb.com.br/artifactory/api/search/artifact?name=" + nome_pacote_war

    try:
      resposta_atf = requests.get(url_consulta_atf, auth=requests.auth.HTTPBasicAuth(usuario_atf,senha_atf))
    except:
      print("\nOCORREU UM ERRO DE COMUNICACAO COM O ARTIFATORY. VERIFIQUE")
      return False

    json_resposta_atf = resposta_atf.json()
  
    try:
        url_resposta_atf = json_resposta_atf['results'][0]['uri']
    except:
        print(nome_pacote_war + " NAO LOCALIZADO NO ARTIFACTORY\n")
        return False

    url_resposta_atf = url_resposta_atf.replace('api/storage/','')

    requisicao_atf = requests.get(url_resposta_atf, auth=requests.auth.HTTPBasicAuth(usuario_atf,senha_atf))

    host_local = os.popen('hostname').read()

    if (ip_console == host_local):
        with open(nome_pacote_war, 'wb') as arquivo_atf:
            arquivo_atf.write(requisicao_atf.content)

        diretorio_existe = os.path.isdir(diretorio_pacote)
        if not diretorio_existe:
            os.mkdir(diretorio_pacote)
            print("DIRETORIO " + diretorio_pacote + " CRIADO.")

        os.rename(nome_pacote_war, diretorio_pacote + "/" + nome_pacote_war)
    else:
      usr_srv = usuario_so + "@" +  ip_console
      usr_srv_caminho = usr_srv + ":" + diretorio_pacote
      comando_ssh = "mkdir " + diretorio_pacote

      expect_ssh = "expect -c 'spawn ssh " + usr_srv + " " + comando_ssh + "; expect 'password:'; send " + senha_so + "\\r; interact'"
      expect_scp = "expect -c 'spawn scp " + nome_pacote_war + " " + usr_srv_caminho + "; expect 'password:'; send " + senha_so + "\\r; interact'"

      saida_ssh = os.popen(expect_ssh).read()
      saida_scp = os.popen(expect_scp).read()

    return True

#------------------------------------------------------------------------------------------------------------------------------

def cria_templates_clusters():
  alias_do_certificado = propriedades['template']['alias_do_certificado']
  caminho_do_certificado = propriedades['template']['caminho_do_certificado']
  caminho_log_general = propriedades['template']['caminho_log_general']
  caminho_log_http = propriedades['template']['caminho_log_http']
  java_home = propriedades['template']['java_home']
  classpath = propriedades['template']['class_path']
  arguments = propriedades['template']['arguments']

  dados_template_serverstart = {
    'javaHome': java_home,
    'classPath': classpath,
    'arguments': arguments
  }

  dados_template_webserverlog = {
    'fileName': caminho_log_http,
    'loggingEnabled': True,
    'rotationType': 'byTime',
    'numberOfFilesLimited': True,
    'fileCount': 8,
    'rotateLogOnStartup': True
  }

  dados_template_log = {
    'fileName': caminho_log_general,
    'rotationType': 'byTime',
    'fileCount': 8,
    'numberOfFilesLimited': True,
    'rotateLogOnStartup': True
  }

  for pacote in pacotes['grupos']:
    if servidor['grupo'] == pacote['id']:
      for item_jvm in pacote['jvms']:
        nome_jvm = item_jvm['nome']
        http_port = item_jvm['porta']
        qtd_instancias = item_jvm['instancias']

        ssl_port = http_port + 35000

        nome_template = "template-" + nome_jvm
        nome_cluster = "cluster-" + nome_jvm

        dados_template = {
          'name': nome_template,
          'listenPort': http_port,
          'listenAddress': ip_console,
          'machine': [ 'machines', machine ],
          'keyStores': 'CustomIdentityAndJavaStandardTrust',
          'customIdentityKeyStoreType': 'JKS',
          'customIdentityKeyStoreFileName' : caminho_do_certificado,
          'customIdentityKeyStorePassPhrase': senha_do_certificado,
          'cluster': [ 'clusters', nome_cluster ]
        }

        dados_template_ssl = {
          'enabled': True,
          'listenPort': ssl_port,
          'serverPrivateKeyAlias': alias_do_certificado,
          'serverPrivateKeyPassPhrase': senha_do_certificado
        }

        dados_cluster = {
          'name': nome_cluster,
          'weblogicPluginEnabled': True
        }

        dados_cluster_dynamicservers = {
          'serverTemplate': [ 'serverTemplates', nome_template ],
          'dynamicClusterSize': qtd_instancias,
          'serverNamePrefix': nome_jvm + '-'
        }

        endpoint_template = "/management/weblogic/latest/edit/serverTemplates"
        endpoint_cluster = "/management/weblogic/latest/edit/clusters"

        endpoint_template_ssl = "/management/weblogic/latest/edit/serverTemplates/" + nome_template + "/SSL"
        endpoint_template_serverstart = "/management/weblogic/latest/edit/serverTemplates/" +  nome_template + "/serverStart"
        endpoint_template_log = "/management/weblogic/latest/edit/serverTemplates/" + nome_template + "/log"
        endpoint_template_webserverlog = "/management/weblogic/latest/edit/serverTemplates/" + nome_template + "/webServer/webServerLog"
        endpoint_cluster_dynamicservers = "/management/weblogic/latest/edit/clusters/" + nome_cluster + "/dynamicServers"

        print("- CRIANDO TEMPLATE/CLUSTER " + nome_jvm + "...")
        resposta = requests.post(url_console + endpoint_cluster, json=dados_cluster, headers = header, auth = (usuario, senha))
        resposta = requests.post(url_console + endpoint_template, json=dados_template, headers = header, auth = (usuario, senha))
        resposta = requests.post(url_console + endpoint_template_ssl, json=dados_template_ssl, headers = header, auth = (usuario, senha))
        resposta = requests.post(url_console + endpoint_template_serverstart, json=dados_template_serverstart, headers = header, auth = (usuario, senha))
        resposta = requests.post(url_console + endpoint_template_log, json=dados_template_log, headers = header, auth = (usuario, senha))
        resposta = requests.post(url_console + endpoint_template_webserverlog, json=dados_template_webserverlog, headers = header, auth = (usuario, senha))
        resposta = requests.post(url_console + endpoint_cluster_dynamicservers, json=dados_cluster_dynamicservers, headers = header, auth = (usuario, senha))

#------------------------------------------------------------------------------------------------------------------------------

def executa_undeploy_deploy(ip_console):
  for pacote in pacotes['grupos']:
    if servidor['grupo'] == pacote['id']:
      for item_pacote in pacote['pacotes']:
        nome_pacote_implantado = ""
        nome_jvm = item_pacote['jvm']
        nome_pacote = item_pacote['nome']
        versao_pacote = item_pacote['versao']
        extensao_pacote = item_pacote['extensao']

        nome_cluster = "cluster-" + nome_jvm
        
        if (extensao_pacote == "tgz"):
          diretorio_pacote = pacotes['diretorio_tgz'] + "/" + nome_pacote
          # nome_pacote_tgz = nome_pacote
          caminho_pacote = diretorio_pacote
        elif (extensao_pacote == "war"):
          diretorio_pacote = pacotes['diretorio_war'] + "/" + nome_pacote
          nome_pacote_war = nome_pacote + "-" + versao_pacote + "." + extensao_pacote
          caminho_pacote = diretorio_pacote + "/" + nome_pacote_war
        else:
          print("EXTENSAO DO PACOTE DEVE SER 'WAR' OU 'TGZ'")
          exit()

        dados_undeploy = {
          'targets':  [ nome_cluster ],
          'deploymentOptions': {}
        }

        dados_deploy = {
          'name': nome_pacote,
          'applicationPath': caminho_pacote,
          'targets': [ nome_cluster ],
          'plan': None,
          'deploymentOptions': { 'appVersion': versao_pacote }
        }

        nome_pacote_em_implantacao = nome_pacote + "%23" + versao_pacote

        resposta_appDeployment = requests.get(url_console + endpoint_appDeployment, headers = header, auth = (usuario, senha))
        for item in resposta_appDeployment.json()['items']:
          if item['applicationName'] == nome_pacote:
            nome_pacote_implantado = item['applicationIdentifier'].replace('#', '%23')

        pacote_existe = os.path.exists(caminho_pacote)

        # if (not pacote_existe):
        #   print("PACOTE " + caminho_pacote + " NAO LOCALIZADO NO DIRETORIO")
        #   print("TENTANDO FAZER O DOWNLOAD A PARTIR DO ARTIFACTORY...\n")
        #   arquivo_baixado = baixa_pacote(diretorio_pacote, ip_console, nome_pacote_war)
        #   if (arquivo_baixado == True):
        #     print("ARQUIVO BAIXADO COM SUCESSO\n")
        #     pacote_existe = True

        endpoint_undeploy = "/management/weblogic/latest/domainRuntime/deploymentManager/appDeploymentRuntimes/" + nome_pacote_implantado + "/undeploy"

        if (nome_pacote_implantado == "") and pacote_existe:
          print("PACOTE NAO LOCALIZADO PARA UNDEPLOY")
          print("EXECUTANDO DEPLOY DO PACOTE: " + nome_pacote_em_implantacao.replace('%23', '-') + "\n")
          deploy = requests.post(url_console + endpoint_deploy, json=dados_deploy, headers = header, auth = (usuario, senha))
        elif (nome_pacote_implantado != nome_pacote_em_implantacao) and pacote_existe:
          print("EXECUTANDO UNDEPLOY DO PACOTE: " + nome_pacote_implantado.replace('%23', '-'))
          undeploy = requests.post(url_console + endpoint_undeploy, json=dados_undeploy, headers = header, auth = (usuario, senha))
          print("EXECUTANDO   DEPLOY DO PACOTE: " + nome_pacote_em_implantacao.replace('%23', '-') + "\n")
          deploy = requests.post(url_console + endpoint_deploy, json=dados_deploy, headers = header, auth = (usuario, senha))

###############################################################################################################################

header = { 'X-Requested-By': 'MyClient', 'Content-Type':'application/json' }

endpoint_startEdit = "/management/weblogic/latest/edit/changeManager/startEdit"
endpoint_activate = "/management/weblogic/latest/edit/changeManager/activate"
endpoint_coletaClusters = "/management/weblogic/latest/serverConfig/clusters"
endpoint_deploy = "/management/weblogic/latest/domainRuntime/deploymentManager/deploy"
endpoint_appDeployment = "/management/weblogic/latest/serverConfig/appDeployments"

try:
  if (len(os.listdir("configs")) == 0):
    print("ARQUIVOS DE CONFIGURACAO NAO LOCALIZADOS")
    print("OS ARQUIVOS DEVEM ESTAR NO DIRETORIO 'configs',")
    print("SEPARADOS POR PRODUTOS E EM DIRETORIO PROPRIO.")
    exit()
  else:
    print("SELECIONE O PRODUTO:")
    lista_produtos = os.listdir("configs")
    lista_produtos.sort()
    for i in range(len(lista_produtos)):
      print("[" + str(i) + "] " + lista_produtos[i])
except:
  exit()

try:
  produto_selecionado = int(raw_input("\nESCOLHA: "))
  produto_selecionado = "configs/" + lista_produtos[produto_selecionado] + "/"
except:
  print("APENAS OS NUMEROS ACIMA SAO VALIDOS")
  print("TENTE NOVAMENTE")
  exit()

estrutura_selecionada = (raw_input("ESTRUTURA [ b: blue / g: green / p: padrao ]: ")).lower()
if (estrutura_selecionada == 'b'):
  estrutura_selecionada = 'blue'
elif (estrutura_selecionada == 'g'):
  estrutura_selecionada = 'green'
elif (estrutura_selecionada == 'p'):
  estrutura_selecionada = 'padrao'

print("\r")

try:
  with open(produto_selecionado + 'properties.json') as json_properties:
      propriedades = json.load(json_properties)

  with open(produto_selecionado + 'hosts.json') as json_hosts:
      hosts = json.load(json_hosts)

  with open(produto_selecionado + 'pacotes.json') as json_pacotes:
      pacotes = json.load(json_pacotes)
except:
  print("ERRO DURANTE A LEITURA DO ARQUIVO JSON")
  exit()

print(">>> DADOS GLOBAIS <<<")
usuario = raw_input("Usuario (Console WL): ")
senha = getpass.getpass("Senha (Console WL): ")

print("\r")

print("SELECIONE A OPCAO: ")
print("[0] CRIAR ESTRUTURA (CLUSTERS/TEMPLATES/DATASOURCES/STARTUPCLASSES)")
print("[1] EXECUTAR DEPLOY (CONFORME ARQUIVO 'PACOTES.JSON')")
print("[2] SAIR")
opcao_selecionada = raw_input("\nOPCAO: ")

print("\r")

if (opcao_selecionada == "0"):
  print(">>> DADOS PARA GERACAO DE TEMPLATES E DATASOURCES <<<")
  senha_do_certificado = raw_input("SENHA DO CERTIFICADO: ")
  senha_datasource = raw_input("SENHA DO DATASOURCE: ")
elif (opcao_selecionada == "1"):
  print(">>> INICIANDO O PROCESSO DE DEPLOY <<<")
  usuario_so = raw_input ("Usuario (Linux): ")
  senha_so = raw_input ("Senha (Linux): ")
elif (opcao_selecionada == "2"):
  print("SAINDO...")
else:
  print("OPCAO INVALIDA")
  print("SAINDO...")
  exit()

for servidor in hosts['servidores']:
  if servidor['estrutura'] == estrutura_selecionada:
    ip_console = servidor['ip']
    machine = servidor['nome']
    porta_console = "7001"
    url_console = "http://" + ip_console + ":" + porta_console

    try:
      lockEdit = requests.post(url_console + endpoint_startEdit, timeout=5, headers = header, auth = (usuario, senha))
    except:
      print("CONSOLE DO SERVIDOR " + servidor['nome'] + " NAO ESTA RESPONDENDO")
      print("EXECUCAO PROSSEGUIRA PARA A PROXIMA CONSOLE, CASO HAJA\n")
      continue

    if (lockEdit.status_code == 401):
      print("CONSOLE: " + machine)
      print("USUARIO E/OU SENHA INCORRETOS")
      print("TENTE NOVAMENTE\n")
      exit()

    if (opcao_selecionada == "0"):
      print("\n>>> PROCESSANDO O SERVIDOR: " + machine + " <<<")
      cria_templates_clusters()
      activate = requests.post(url_console + endpoint_activate, headers = header, auth = (usuario, senha))
      lockEdit = requests.post(url_console + endpoint_startEdit, headers = header, auth = (usuario, senha))
      cria_startupclasses()
      cria_datasource()
      activate = requests.post(url_console + endpoint_activate, headers = header, auth = (usuario, senha))
    elif (opcao_selecionada == "1"):
      print("\n>>> PROCESSANDO O SERVIDOR: " + machine + " <<<")
      executa_undeploy_deploy(ip_console)
      activate = requests.post(url_console + endpoint_activate, headers = header, auth = (usuario, senha))
    else:
      exit()
    
