-- Eixos B e C - Rendimento, fluxo e aprendizagem (números oficiais do INEP, sem recálculo).

-- B1 (aprovação, reprovação, abandono) e B2 (distorção idade-série): município, UF, Brasil e escola.
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, co_entidade, ano, cod_etapa, cod_recorte, valor, status_valor,
                           data_coleta, referencia, cod_fonte_valor)
SELECT CASE WHEN r.medida = 'distorcao_idade_serie' THEN 'B2' ELSE 'B1.' || r.medida END,
       r.cod_territorio, r.co_entidade, r.ano, r.cod_etapa, r.cod_recorte, r.valor, r.status_valor, r.data_coleta,
       'INEP - Indicadores Educacionais', f.cod_fonte
FROM core.v_fato_rendimento r
JOIN core.dim_fonte f USING (id_fonte);

-- C1 e C2: Ideb, meta, notas do Saeb e indicador de rendimento. Vale a edição mais recente que
-- trouxe o valor (o INEP revisa números já publicados); a edição fica em "referencia".
WITH mapa(componente, cod_indicador) AS (
  VALUES ('ideb', 'C1'), ('meta_ideb', 'C1.meta'), ('matematica', 'C2.matematica'),
         ('lingua_portuguesa', 'C2.lingua_portuguesa'), ('indicador_rendimento', 'C2.rendimento_ideb')
),
ultima AS (
  SELECT DISTINCT ON (a.componente, a.cod_territorio, a.co_entidade, a.ano, a.cod_etapa, a.cod_recorte)
         a.*
  FROM core.v_fato_avaliacao a
  WHERE a.componente IN (SELECT componente FROM mapa)
  ORDER BY a.componente, a.cod_territorio, a.co_entidade, a.ano, a.cod_etapa, a.cod_recorte, a.edicao DESC
)
INSERT INTO tmp_indicador (cod_indicador, cod_territorio, co_entidade, ano, cod_etapa, cod_recorte, valor, status_valor,
                           data_coleta, referencia, nota)
SELECT m.cod_indicador, u.cod_territorio, u.co_entidade, u.ano, u.cod_etapa, u.cod_recorte, u.valor, u.status_valor,
       u.data_coleta, 'Ideb - divulgação ' || u.edicao || ' (' || u.instrumento || ')',
       CASE WHEN u.ano = 2021 THEN 'Resultado de 2021 (Saeb aplicado durante a pandemia): comparar com cautela.' END
FROM ultima u
JOIN mapa m USING (componente);
