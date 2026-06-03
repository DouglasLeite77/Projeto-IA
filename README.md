## 📊 Relatório Técnico

### 1. Obtenção e Preparação do Dataset

O dataset foi obtido através da **Google Fact Check API**, uma ferramenta que fornece verificações de fatos de múltiplos verificadores ao redor do mundo. O projeto realiza buscas automáticas usando palavras-chave relacionadas a política brasileira, incluindo:
- Nomes de políticos: Lula, Bolsonaro, Ciro Gomes, Haddad, Marina Silva, etc.
- Eventos políticos: eleições, campanhas, votações, reformas
- Órgãos e instituições: STF, TSE, Congresso, Senado
- Temas polêmicos: corrupção, fraude, lava jato, fake news

**Processo de coleta:**
1. Iteração sobre lista de palavras-chave (≤50 keywords)
2. Requisições paginadas à API com tratamento de rate-limiting (retry automático)
3. Mapeamento de ratings (true/false/mostly true/mostly false) para labels binários
4. Armazenamento em CSV com campos: `claim`, `label`, `source`, `date`, `notes`, `url`

**Formato do dataset:**
```
claim              → Texto da afirmação
label              → VERDADEIRO ou FALSO (binário)
source             → Verificador da afirmação
date               → Data da verificação
notes              → Observações adicionais
url                → Link para a verificação completa
```

### 2. Técnicas de Pré-processamento

O pré-processamento de texto é crucial para melhorar a qualidade dos dados de entrada. As técnicas utilizadas incluem:

#### 2.1 Normalização de Texto (`text_preprocessing.py`)
- **Conversão para minúsculas**: Padroniza o texto
- **Remoção de acentuação**: Converte caracteres acentuados (é → e, ã → a)
- **Remoção de URLs**: Elimina links que não agregam informação
- **Remoção de caracteres especiais**: Mantém apenas caracteres alfanuméricos e espaços
- **Tokenização**: Divide o texto em palavras individuais

#### 2.2 Remoção de Stopwords
- Utiliza lista customizada de stopwords em português
- Remove palavras muito comuns (de, o, a, em, etc.) que não agregam significado semântico
- Arquivo: `backend/data/pt_stopwords.txt`

#### 2.3 Stemming
- Utiliza **SnowballStemmer** do NLTK para português
- Reduz palavras às suas raízes (exemplo: "correndo", "correr", "corre" → "corr")
- Melhora a generalização do modelo

#### 2.4 Limpeza de Dataset (`scripts/clean_dataset.py`)
- **Deduplicação**: Remove afirmações duplicadas (após normalização)
- **Filtragem de labels**: Mantém apenas registros com label "true" ou "false"
- **Remoção de registros vazios**: Elimina linhas sem conteúdo válido
- Resultado: Dataset limpo armazenado em `backend/data/cleaned_dataset.csv`

### 3. Algoritmo Escolhido

O projeto implementa uma **Pipeline de Classificação Binária** usando scikit-learn com três algoritmos disponíveis:

#### 3.1 Algoritmo Padrão: Logistic Regression
- **Razão da escolha**: Rápido, eficiente, interpretável e funciona bem com dados textuais
- **Hiperparâmetros**: `max_iter=2000, class_weight='balanced'`
- **Class weight balanceado**: Compensa desbalanceamento de classes

#### 3.2 Alternativas Implementadas
- **Multinomial Naive Bayes**: Rápido, ideal para dados de alta dimensionalidade
- **Support Vector Machine (SVM)**: Excelente para separação de classes, com `probability=True`

#### 3.3 Pipeline Completo
```
TextPreprocessor (normalização + limpeza)
        ↓
TfidfVectorizer (features: 5000, n-gramas: 1-3)
        ↓
Classificador (LogisticRegression, NB ou SVM)
```

### 4. Treinamento do Modelo

#### 4.1 Preparação dos Dados
- **Divisão Train/Test**: 75% treinamento, 25% teste
- **Estratificação**: Mantém proporção de classes em ambos os conjuntos
- **Random state**: 42 (reprodutibilidade)

#### 4.2 Extração de Features
- **TF-IDF (Term Frequency-Inverse Document Frequency)**:
  - Máximo de features: 5000 palavras
  - N-gramas: (1,3) - combina unigramas, bigramas e trigramas
  - Captura contexto e combinações de palavras

#### 4.2 Processo de Treinamento
1. Leitura do dataset (preferência: `cleaned_dataset.csv` > `initial_dataset.csv`)
2. Validação de records com labels válidos
3. Divisão automática train/test
4. Carregamento de stopwords em português
5. Seleção do algoritmo (via variável de ambiente `MODEL_ALGO`)
6. Ajuste do pipeline
7. Predição no conjunto de teste
8. Geração de relatório de classificação
9. Serialização do modelo com joblib

**Comando de treinamento:**
```powershell
python -m backend.scripts.train_model [algoritmo]
# Algoritmos: logreg (padrão), nb (Naive Bayes), svm (SVM)
```

### 5. Métricas de Avaliação

O modelo é avaliado usando métricas padrão de classificação binária:

#### 5.1 Accuracy (Acurácia)
- **Definição**: Percentual de predições corretas entre todas as predições
- **Fórmula**: `(TP + TN) / (TP + TN + FP + FN)`
- **Interpretação**: Métrica geral de performance

#### 5.2 Precision (Precisão)
- **Definição**: Percentual de predições positivas que foram corretas
- **Fórmula**: `TP / (TP + FP)`
- **Interpretação**: Minimiza falsos positivos

#### 5.3 Recall (Sensibilidade)
- **Definição**: Percentual de casos positivos identificados corretamente
- **Fórmula**: `TP / (TP + FN)`
- **Interpretação**: Minimiza falsos negativos

#### 5.4 F1-Score
- **Definição**: Média harmônica entre Precision e Recall
- **Fórmula**: `2 × (Precision × Recall) / (Precision + Recall)`
- **Interpretação**: Métrica balanceada para dados desbalanceados

#### 5.5 Classification Report
O script de treinamento gera um relatório com:
- Precision, Recall e F1-Score por classe
- Suporte (número de amostras) por classe
- Macro average (média simples)
- Weighted average (média ponderada pelo suporte)

**Exemplo de saída:**
```
              precision    recall  f1-score   support

        false       0.8234    0.7891    0.8060       234
        true        0.7956    0.8234    0.8092       218

    accuracy                          0.8056       452
   macro avg       0.8095    0.8062    0.8076       452
weighted avg       0.8098    0.8056    0.8077       452
```

### 6. Dificuldades Encontradas Durante o Desenvolvimento

#### 6.1 Limitações de Dados
- **Dataset pequeno**: A Google Fact Check API retorna número limitado de verificações para queries específicas
- **Desbalanceamento de classes**: Propensão a mais registros de uma classe que outra
- **Qualidade variável**: Nem todas as verificações têm a mesma confiabilidade

#### 6.2 Contexto Cultural e Linguístico
- **Adaptação para português**: Necessidade de stopwords em português e stemming correto
- **Variações regionais**: Diferenças entre português brasileiro e português europeu
- **Nomes próprios**: Dificuldade em processar nomes de políticos e locais

#### 6.3 Integração com API Externa
- **Rate-limiting**: Limites de requisições por minuto/hora
- **Latência**: Coleta de dados é lenta e requer retry automático
- **Dependência**: Projeto depende de disponibilidade e formato da API Google

#### 6.4 Desempenho de Modelos
- **Overfitting**: Risco com dataset pequeno
- **Trade-off Precision vs Recall**: Difícil otimizar ambas simultaneamente
- **Generalização**: Dificuldade em garantir bom desempenho em dados não vistos

#### 6.5 Infraestrutura
- **Armazenamento**: Necessidade de persistência do modelo treinado
- **Reprodutibilidade**: Garantir que modelos treinados produzam resultados consistentes
- **Versionamento**: Rastrear mudanças no dataset e modelo

### 7. Melhorias Futuras

#### 7.1 Ampliação de Dataset
- Integrar múltiplas fontes de verificação de fatos
- Expandir para outros domínios além de política
- Coletar dados de redes sociais e fontes públicas
- Implementar anotação manual colaborativa

#### 7.2 Modelos Mais Avançados
- **Transfer Learning**: Usar modelos pré-treinados (BERT, RoBERTa em português)
- **Deep Learning**: Redes neurais recorrentes (LSTM, GRU)
- **Ensemble**: Combinar múltiplos modelos para melhor performance
- **Active Learning**: Selecionar dados mais informativos para anotação

#### 7.3 Análise Aprofundada
- **Análise de Sentimentos**: Detectar viés emocional nas afirmações
- **Detecção de entidades**: Identificar pessoas, locais, organizações mencionadas
- **Análise de contexto**: Considerar contexto temporal e geográfico
- **Explicabilidade**: Implementar LIME ou SHAP para explicar predições

#### 7.4 Métricas e Avaliação
- **Validação cruzada (k-fold)**: Melhor estimativa de performance
- **Matriz de confusão**: Análise visual de acertos e erros
- **Curvas ROC e AUC**: Avaliar trade-off entre taxa positiva e falsa
- **Análise por subgrupos**: Performance em diferentes categorias

#### 7.5 Infraestrutura e Deploy
- **Containerização**: Docker para facilitar deploy
- **CI/CD**: Pipeline automático de teste e deploy
- **Monitoramento**: Acompanhar performance do modelo em produção
- **Atualização automática**: Retreinamento com novos dados periodicamente

#### 7.6 Interface e UX
- **Explicações em português**: Detalhar por que uma afirmação é classificada como verdadeira/falsa
- **Confidence scores**: Mostrar nível de confiança da predição
- **Histórico**: Rastrear avaliações anteriores
- **Feedback dos usuários**: Coletar dados para melhorar o modelo

---

## Como usar

1. Instale dependências do backend:
   ```powershell
   cd "c:\Users\User\Documents\Nova pasta\Projeto IA\backend"
   python -m pip install -r requirements.txt
   ```

2. Coletar verificações usando a Google Fact Check API (usa a chave em `.env`):
   ```powershell
   cd "c:\Users\User\Documents\Nova pasta\Projeto IA"
   python backend/scripts/collect_factchecks.py
   ```

3. Limpar e deduplicar o dataset:
   ```powershell
   python backend/scripts/clean_dataset.py
   ```

4. Treinar o modelo (ou use o endpoint `/retrain`):
   ```powershell
   python -m backend.scripts.train_model [algoritmo]
   # Algoritmos: logreg (padrão), nb (Naive Bayes), svm (SVM)
   # ou iniciar o backend e chamar /retrain
   uvicorn backend.app:app --reload --port 8000
   # então POST http://127.0.0.1:8000/retrain
   ```

5. Execute o backend (se não estiver rodando):
   ```powershell
   uvicorn backend.app:app --reload --port 8000
   ```

6. Abra o frontend em `frontend/index.html` ou sirva via servidor estático.

## Observações
- A API de fact-check exige chave de API Google em `GOOGLE_API_KEY`.
- Você pode definir a chave em um arquivo `.env` na raiz do projeto ou como variável de ambiente.
- Um exemplo de arquivo está em `.env.example`.
- O dataset inicial está em `backend/data/initial_dataset.csv` e o dataset limpo em `backend/data/cleaned_dataset.csv`.
- O modelo salvo é gerenciado em `backend/model/model.joblib`.
