# Upload de documento no processo

Como servidor, quero anexar documentos a um processo para manter o histórico completo.

## Critérios de aceite

- Só é possível anexar documento em processo com situação "Aberto".
- São aceitos os formatos PDF, PNG e JPG, com até 20 MB por arquivo.
- O sistema permite anexar até 10 arquivos por processo.
- Cada anexo registra data, hora e a matrícula do servidor que anexou.
- Ao tentar anexar o 11º arquivo, o sistema exibe "Limite de 10 anexos atingido".
- Anexo em processo com situação "Arquivado" é bloqueado com a mensagem
  "Processo arquivado não aceita novos anexos".
