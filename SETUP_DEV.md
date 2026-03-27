# Setup (Desenvolvimento)

Pequeno guia para configurar o ambiente de desenvolvimento do projeto `Financeiro-2026` no Windows.

Passos rápidos:

1. Abra o PowerShell na pasta raiz do projeto.
2. (Opcional) Permita execução temporária de scripts:

    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

3. Rode o helper (cria `.venv` e instala dependências):

    .\setup_dev.ps1

    # Se quiser instalar as Build Tools (leva muito tempo e requer winget/admin):
    .\setup_dev.ps1 -InstallBuildTools

4. Ative o ambiente virtual:

    .\.venv\Scripts\Activate.ps1

5. Inicie o app com Streamlit:

    python -m streamlit run app.py

Observações importantes:

- Se estiver usando Python muito novo (ex: 3.14), alguns pacotes podem não ter wheels disponíveis; use Python 3.11 para compatibilidade ampla.
- Se a instalação de pacotes falhar por falta de compilador C/C++, instale as "Build Tools for Visual Studio" (workload C++). O script pode tentar instalar via `winget` com `-InstallBuildTools`.
- Para OCR/extração de PDFs você precisa também dos binários externos:
  - Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki
  - Poppler (pdftoppm): https://poppler.freedesktop.org/

Se quiser, posso também gerar uma versão `setup_dev.bat` ou instruções para Conda.
