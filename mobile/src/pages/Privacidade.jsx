import { X } from 'lucide-react'
import { T } from '../ui.jsx'

export default function Privacidade({ onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center p-4"
         style={{ background: 'rgba(4,8,20,0.9)', backdropFilter: 'blur(6px)' }}>
      <div className="rounded-2xl flex flex-col overflow-hidden w-full max-w-2xl"
           style={{ background: T.surface, border: `1px solid ${T.border}`, maxHeight: '90vh' }}>

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 shrink-0"
             style={{ borderBottom: `1px solid ${T.border}`, background: T.s2 }}>
          <div>
            <h2 className="text-[15px] font-bold text-slate-100">Política de Privacidade</h2>
            <p className="text-[11px] mt-0.5" style={{ color: T.muted }}>MilkShow Enterprise · Adequada à LGPD (Lei 13.709/2018)</p>
          </div>
          {onClose && (
            <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/5 transition-colors" style={{ color: T.sub }}>
              <X size={16} />
            </button>
          )}
        </div>

        {/* Content */}
        <div className="overflow-y-auto flex-1 px-6 py-5 space-y-5 text-[13px] leading-relaxed" style={{ color: '#cbd5e1' }}>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">1. Controlador dos Dados</h3>
            <p>O controlador dos seus dados pessoais é a <strong className="text-slate-200">MilkShow Tecnologia Ltda.</strong>, responsável pelo tratamento de dados conforme a Lei Geral de Proteção de Dados (LGPD — Lei nº 13.709/2018). Contato do Encarregado de Dados (DPO): <strong className="text-slate-200">privacidade@milshow.com.br</strong>.</p>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">2. Dados Coletados</h3>
            <p className="mb-2">Coletamos as seguintes categorias de dados:</p>
            <ul className="space-y-1.5 ml-4">
              <li><span className="text-slate-200 font-medium">Dados de Cadastro:</span> nome, e-mail, telefone, CPF/CNPJ, endereço da propriedade.</li>
              <li><span className="text-slate-200 font-medium">Dados da Fazenda:</span> nome da propriedade, localização (município/estado), configurações operacionais.</li>
              <li><span className="text-slate-200 font-medium">Dados Operacionais:</span> registros de produção de leite, rebanho (animais, raças, status), financeiro (receitas e despesas), estoque, protocolos sanitários.</li>
              <li><span className="text-slate-200 font-medium">Dados de Uso:</span> logs de acesso, endereço IP, tipo de dispositivo, navegador, interações com o sistema.</li>
              <li><span className="text-slate-200 font-medium">Comunicações:</span> mensagens trocadas com o assistente WhatsApp (processadas por IA).</li>
            </ul>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">3. Finalidade do Tratamento</h3>
            <ul className="space-y-1.5 ml-4">
              <li><strong className="text-slate-200">Execução do Contrato:</strong> prestação dos serviços de gestão rural contratados.</li>
              <li><strong className="text-slate-200">Legítimo Interesse:</strong> melhoria do serviço, segurança da plataforma, prevenção de fraudes.</li>
              <li><strong className="text-slate-200">Consentimento:</strong> envio de comunicações de marketing, novidades e atualizações (você pode revogar a qualquer momento).</li>
              <li><strong className="text-slate-200">Cumprimento Legal:</strong> obrigações fiscais, contábeis e regulatórias aplicáveis.</li>
            </ul>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">4. Base Legal</h3>
            <p>O tratamento é realizado com base no Art. 7º da LGPD: consentimento do titular, execução de contrato, legítimo interesse e cumprimento de obrigação legal. Para dados sensíveis (saúde animal, dados biométricos de animais), aplicamos medidas reforçadas de segurança.</p>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">5. Compartilhamento de Dados</h3>
            <p className="mb-2">Seus dados poderão ser compartilhados com:</p>
            <ul className="space-y-1 ml-4">
              <li><strong className="text-slate-200">Google Firebase:</strong> armazenamento seguro de dados na nuvem (servidores nos EUA, com cláusulas contratuais padrão).</li>
              <li><strong className="text-slate-200">Groq / Google Gemini:</strong> processamento de linguagem natural para o assistente IA (dados anonimizados).</li>
              <li><strong className="text-slate-200">Evolution API:</strong> integração com WhatsApp para o bot assistente.</li>
              <li><strong className="text-slate-200">Autoridades:</strong> quando exigido por lei, ordem judicial ou órgão regulador.</li>
            </ul>
            <p className="mt-2">Não vendemos, alugamos ou compartilhamos seus dados com terceiros para fins comerciais.</p>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">6. Transferência Internacional</h3>
            <p>Alguns dados são processados fora do Brasil (Google Firebase nos EUA). Garantimos que essas transferências seguem salvaguardas adequadas conforme Art. 33 da LGPD, incluindo cláusulas contratuais padrão da Comissão Europeia e certificações de adequação.</p>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">7. Retenção de Dados</h3>
            <ul className="space-y-1 ml-4">
              <li><strong className="text-slate-200">Conta ativa:</strong> dados mantidos durante toda a vigência do contrato.</li>
              <li><strong className="text-slate-200">Após cancelamento:</strong> dados disponíveis para exportação por 60 dias, depois excluídos.</li>
              <li><strong className="text-slate-200">Logs de acesso:</strong> mantidos por 6 meses (Marco Civil da Internet).</li>
              <li><strong className="text-slate-200">Dados fiscais:</strong> mantidos por 5 anos conforme legislação fiscal.</li>
            </ul>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">8. Segurança dos Dados</h3>
            <p>Adotamos medidas técnicas e organizacionais para proteger seus dados: criptografia em trânsito (HTTPS/TLS 1.3), criptografia em repouso no Firebase, autenticação multifator disponível, backups semanais automáticos, controle de acesso por perfil (RBAC), e monitoramento contínuo de incidentes de segurança.</p>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">9. Seus Direitos (LGPD Art. 18)</h3>
            <p className="mb-2">Você tem os seguintes direitos em relação aos seus dados pessoais:</p>
            <ul className="space-y-1 ml-4">
              <li>✓ <strong className="text-slate-200">Confirmação e Acesso:</strong> saber quais dados temos sobre você.</li>
              <li>✓ <strong className="text-slate-200">Correção:</strong> corrigir dados incompletos ou desatualizados.</li>
              <li>✓ <strong className="text-slate-200">Anonimização ou Exclusão:</strong> eliminar dados desnecessários.</li>
              <li>✓ <strong className="text-slate-200">Portabilidade:</strong> exportar seus dados em formato aberto (CSV, JSON).</li>
              <li>✓ <strong className="text-slate-200">Revogação do Consentimento:</strong> cancelar autorizações específicas.</li>
              <li>✓ <strong className="text-slate-200">Oposição:</strong> opor-se ao tratamento em determinadas circunstâncias.</li>
              <li>✓ <strong className="text-slate-200">Eliminação:</strong> solicitar exclusão completa da conta e dados.</li>
            </ul>
            <p className="mt-2">Para exercer seus direitos, envie solicitação para <strong className="text-slate-200">privacidade@milshow.com.br</strong>. Atenderemos em até 15 dias úteis.</p>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">10. Cookies e Tecnologias Similares</h3>
            <p>Utilizamos localStorage e sessionStorage para manter sua sessão ativa e preferências (posição dos botões, última aba visitada). Não utilizamos cookies de rastreamento de terceiros para fins publicitários.</p>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">11. Menores de Idade</h3>
            <p>O Serviço é destinado exclusivamente a maiores de 18 anos ou emancipados. Não coletamos intencionalmente dados de menores. Caso identifiquemos tal situação, excluiremos os dados imediatamente.</p>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">12. Incidentes de Segurança</h3>
            <p>Em caso de incidente de segurança que possa afetar seus dados, notificaremos a ANPD (Autoridade Nacional de Proteção de Dados) e os titulares afetados no prazo máximo de 72 horas após a descoberta, conforme exigido pela LGPD.</p>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">13. Alterações nesta Política</h3>
            <p>Podemos atualizar esta Política periodicamente. Alterações significativas serão comunicadas por e-mail e notificação no aplicativo com antecedência de 30 dias. O uso continuado após a vigência das alterações implica aceitação.</p>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">14. Contato e Reclamações</h3>
            <p>DPO (Encarregado de Dados): <strong className="text-slate-200">privacidade@milshow.com.br</strong><br />
            Você também pode registrar reclamações junto à ANPD: <span className="text-blue-400">anpd.gov.br</span></p>
          </section>

          <p className="text-[11px] pt-3 pb-1 border-t" style={{ color: T.muted, borderColor: T.border }}>
            Última atualização: 28 de junho de 2026 · Versão 1.0
          </p>
        </div>
      </div>
    </div>
  )
}
