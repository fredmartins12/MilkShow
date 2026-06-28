import { X } from 'lucide-react'
import { T } from '../ui.jsx'

export default function Termos({ onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center p-4"
         style={{ background: 'rgba(4,8,20,0.9)', backdropFilter: 'blur(6px)' }}>
      <div className="rounded-2xl flex flex-col overflow-hidden w-full max-w-2xl"
           style={{ background: T.surface, border: `1px solid ${T.border}`, maxHeight: '90vh' }}>

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 shrink-0"
             style={{ borderBottom: `1px solid ${T.border}`, background: T.s2 }}>
          <div>
            <h2 className="text-[15px] font-bold text-slate-100">Termos de Uso</h2>
            <p className="text-[11px] mt-0.5" style={{ color: T.muted }}>MilkShow Enterprise — versão 1.0 · Junho 2026</p>
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
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">1. Aceitação dos Termos</h3>
            <p>Ao criar uma conta ou utilizar o MilkShow Enterprise ("Serviço"), você declara ter lido, compreendido e concordado com estes Termos de Uso. Caso não concorde, não utilize o Serviço. O uso continuado após alterações nos Termos implica aceitação das mudanças.</p>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">2. Descrição do Serviço</h3>
            <p>O MilkShow Enterprise é uma plataforma SaaS de gestão para fazendas leiteiras, oferecendo: registro de produção de leite, gestão de rebanho, controle financeiro, armazém, protocolos sanitários, assistente de inteligência artificial via WhatsApp e relatórios gerenciais. O Serviço é prestado pela <strong className="text-slate-200">MilkShow Tecnologia Ltda.</strong>, com acesso pelo endereço <strong className="text-slate-200">milshow.com.br</strong>.</p>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">3. Cadastro e Segurança da Conta</h3>
            <p>Você é responsável por manter a confidencialidade de suas credenciais de acesso. Notifique-nos imediatamente em caso de uso não autorizado. A MilkShow não se responsabiliza por perdas decorrentes do compartilhamento indevido de credenciais. É permitido apenas um cadastro por CPF/CNPJ.</p>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">4. Licença de Uso</h3>
            <p>Concedemos a você uma licença limitada, não exclusiva, não transferível e revogável para utilizar o Serviço exclusivamente para fins de gestão da sua propriedade rural. É vedado: (a) sublicenciar ou revender o acesso; (b) realizar engenharia reversa; (c) utilizar bots para extração massiva de dados; (d) utilizar o Serviço para fins ilegais.</p>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">5. Dados e Propriedade Intelectual</h3>
            <p>Você mantém a propriedade dos dados inseridos na plataforma (dados da sua fazenda, animais, produções e finanças). A MilkShow detém todos os direitos sobre a plataforma, código-fonte, marca, design e funcionalidades. Você concede à MilkShow licença para processar seus dados conforme necessário para a prestação do Serviço.</p>
            <p className="mt-2">Os dados agregados e anonimizados poderão ser utilizados pela MilkShow para pesquisa e melhoria do serviço, sem identificar sua fazenda individualmente.</p>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">6. Planos e Pagamentos</h3>
            <p>O Serviço oferece período de trial gratuito. Após o período trial, é necessária a contratação de um plano pago. Preços e condições estão disponíveis em milshow.com.br/planos. O não pagamento implica suspensão temporária e, após 30 dias, encerramento da conta. Em caso de encerramento, os dados ficam disponíveis para exportação por 60 dias.</p>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">7. Disponibilidade e SLA</h3>
            <p>A MilkShow empreende esforços razoáveis para manter o Serviço disponível 24/7, mas não garante disponibilidade ininterrupta. Manutenções programadas serão comunicadas com antecedência de 24 horas via e-mail ou WhatsApp. A MilkShow não se responsabiliza por indisponibilidades causadas por fatores externos (provedores de internet, falhas de energia, casos fortuitos ou força maior).</p>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">8. Limitação de Responsabilidade</h3>
            <p>A MilkShow não se responsabiliza por: (a) decisões tomadas com base nas informações exibidas no sistema; (b) perdas de produção, financeiras ou negociais decorrentes do uso ou impossibilidade de uso do Serviço; (c) imprecisões nos dados inseridos pelo próprio usuário; (d) danos indiretos, incidentais ou consequenciais. A responsabilidade total da MilkShow ficará limitada ao valor pago nos últimos 3 meses de serviço.</p>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">9. Rescisão</h3>
            <p>Qualquer parte pode rescindir o contrato mediante aviso prévio de 30 dias. A MilkShow pode encerrar imediatamente em caso de violação destes Termos, uso fraudulento ou conduta abusiva. Em qualquer hipótese de encerramento, você poderá exportar seus dados dentro do prazo estabelecido.</p>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">10. Legislação Aplicável</h3>
            <p>Estes Termos são regidos pelas leis da República Federativa do Brasil. Fica eleito o foro da Comarca de João Pessoa — PB para dirimir quaisquer controvérsias, com renúncia de qualquer outro, por mais privilegiado que seja.</p>
          </section>

          <section>
            <h3 className="font-semibold text-slate-100 text-[14px] mb-2">11. Contato</h3>
            <p>Para dúvidas sobre estes Termos: <strong className="text-slate-200">suporte@milshow.com.br</strong> | WhatsApp: (83) 98235-2153</p>
          </section>

          <p className="text-[11px] pt-3 pb-1 border-t" style={{ color: T.muted, borderColor: T.border }}>
            Última atualização: 28 de junho de 2026
          </p>
        </div>
      </div>
    </div>
  )
}
