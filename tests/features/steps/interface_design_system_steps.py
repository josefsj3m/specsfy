import json
from pathlib import Path

from behave import given, then, when


ROOT = Path(__file__).resolve().parents[3]
TABLE_ASSET = (
    ROOT
    / "specialists"
    / "specsfy-specialist-react-ui-components"
    / "assets"
    / "components"
    / "data-display"
    / "table.tsx"
)
LARAVEL_APP_LAYOUT = ROOT / "example" / "resources" / "js" / "layouts" / "app-layout.tsx"
LARAVEL_BREADCRUMBS = ROOT / "example" / "resources" / "js" / "components" / "breadcrumbs.tsx"
LARAVEL_BREADCRUMB_PRIMITIVE = ROOT / "example" / "resources" / "js" / "components" / "ui" / "breadcrumb.tsx"


@given("o template global de design system do Specsfy")
def given_design_system_template(context) -> None:
    context.template = (ROOT / "skills" / "templates" / "DESIGNSYSTEM.MD").read_text(
        encoding="utf-8"
    )


@when("os padrões de CRUD são lidos")
def when_crud_patterns_are_read(context) -> None:
    context.crud = context.template


@when("os padrões comuns de interface são lidos")
def when_common_interface_patterns_are_read(context) -> None:
    context.common_interface = context.template


@then("dashboards usam PageHeader, filtros e indicadores com contexto")
def then_dashboards_have_context(context) -> None:
    assert "Dashboard canônico" in context.common_interface
    assert "PageHeader" in context.common_interface
    assert "filtros" in context.common_interface
    assert "KPI" in context.common_interface


@then("primitives de shadcn/ui e blocos ReUI podem compor CRUDs e dashboards")
def then_component_blocks_are_available(context) -> None:
    assert "shadcn/ui" in context.common_interface
    assert "ReUI" in context.common_interface


@then("a interface cobre teclado, foco, estados e responsividade")
def then_interface_quality_is_covered(context) -> None:
    for term in ("teclado", "foco", "estados", "responsividade"):
        assert term in context.common_interface


@given("o contrato de interação do DataGrid do Specsfy")
def given_datagrid_interaction_contract(context) -> None:
    context.datagrid = (
        (ROOT / "skills" / "templates" / "DESIGNSYSTEM.MD").read_text(
            encoding="utf-8"
        )
        + TABLE_ASSET.read_text(encoding="utf-8")
    )


@when("a navegação da lista é lida")
def when_list_navigation_is_read(context) -> None:
    context.row_navigation = context.datagrid


@then("toda a linha abre o detalhe por clique e teclado")
def then_full_row_opens_detail(context) -> None:
    assert "linha inteira" in context.row_navigation
    assert "teclado" in context.row_navigation
    assert "data-row-link" in context.row_navigation


@then("ações internas não disparam a navegação da linha")
def then_inner_actions_do_not_navigate(context) -> None:
    assert "ações internas" in context.row_navigation
    assert "TableRowAction" in context.row_navigation
    assert "data-row-action" in context.row_navigation


@then("todas as telas CRUD reutilizam o mesmo PageHeader componentizado")
def then_crud_pages_reuse_page_header(context) -> None:
    assert "PageHeader" in context.crud
    assert "reutiliz" in context.crud
    assert "component" in context.crud


@then("a listagem usa DataGrid em largura total com a coluna ID visível")
def then_crud_list_has_full_width_id(context) -> None:
    assert "DataGrid" in context.crud
    assert "largura total" in context.crud
    assert "ID" in context.crud


@then("cada linha leva ao detalhe e oferece editar e apagar")
def then_crud_row_has_actions(context) -> None:
    assert "linha" in context.crud
    assert "detalhe" in context.crud
    assert "editar" in context.crud.casefold()
    assert "apagar" in context.crud.casefold()


@given("o contrato de implementação visual do Specsfy")
def given_visual_implementation_contract(context) -> None:
    context.visual_contract = (
        (ROOT / "skills" / "Spec.md").read_text(encoding="utf-8")
        + (ROOT / "skills" / "templates" / "Tasks.md").read_text(encoding="utf-8")
        + (ROOT / "skills" / "specsfy-07-implement" / "SKILL.md").read_text(encoding="utf-8")
    )


@when("a revisão de desenvolvimento é lida")
def when_visual_development_review_is_read(context) -> None:
    context.visual_review = context.visual_contract


@then("a conferência visual é obrigatória mesmo sem pedido da pessoa")
def then_visual_review_is_mandatory(context) -> None:
    assert "obrigat" in context.visual_review
    assert "mesmo sem" in context.visual_review


@then("ela verifica bordas espaçamentos margens padding e tipografia do sistema")
def then_visual_review_checks_system_tokens(context) -> None:
    for term in ("bordas", "espaçamentos", "margens", "padding", "tipografia"):
        assert term in context.visual_review


@given("o contrato de navegação contextual do Specsfy")
def given_context_navigation_contract(context) -> None:
    context.context_navigation = (
        (ROOT / "skills" / "templates" / "DESIGNSYSTEM.MD").read_text(
            encoding="utf-8"
        )
        + (ROOT / "skills" / "templates" / "Interface.md").read_text(
            encoding="utf-8"
        )
        + LARAVEL_APP_LAYOUT.read_text(encoding="utf-8")
    )
    context.laravel_breadcrumbs = LARAVEL_BREADCRUMBS.read_text(encoding="utf-8")
    context.laravel_breadcrumb_primitive = LARAVEL_BREADCRUMB_PRIMITIVE.read_text(encoding="utf-8")


@when("o breadcrumb global é lido")
def when_global_breadcrumb_is_read(context) -> None:
    context.breadcrumb = context.context_navigation


@then("toda tela exibe equipe, módulo e tela atual")
def then_every_screen_exposes_context(context) -> None:
    for term in (
        "Breadcrumb",
        "equipe",
        "módulo",
        "tela atual",
        "currentTeam.name",
    ):
        assert term in context.breadcrumb


@then("Laravel reaproveita o breadcrumb existente do layout")
def then_laravel_reuses_existing_breadcrumb(context) -> None:
    assert "AppLayoutTemplate breadcrumbs={breadcrumbsWithTeam}" in context.breadcrumb
    assert "export function Breadcrumbs" in context.laravel_breadcrumbs
    assert 'aria-label="breadcrumb"' in context.laravel_breadcrumb_primitive


@then("listas usam DataGrid com PageHeader")
def then_lists_use_datagrid(context) -> None:
    assert "DataGrid" in context.crud
    assert "PageHeader" in context.crud


@then("detalhes usam DetailLists com PageHeader")
def then_details_use_detaillists(context) -> None:
    assert "DetailLists" in context.crud
    assert "PageHeader" in context.crud


@then("criação e edição usam seções com duas colunas responsivas")
def then_forms_use_sections_and_columns(context) -> None:
    for term in ("seções", "duas colunas", "grid-cols-2", "mobile"):
        assert term in context.crud


@then("erros de campo aparecem em vermelho abaixo do campo")
def then_field_errors_are_visible(context) -> None:
    assert "vermelho" in context.crud
    assert "abaixo" in context.crud


@given("a skill especialista de design system do Specsfy")
def given_design_system_skill(context) -> None:
    context.skill = (
        ROOT / "specialists" / "specsfy-specialist-design-system" / "SKILL.md"
    ).read_text(encoding="utf-8")


@when("sua política de direção é lida")
def when_direction_policy_is_read(context) -> None:
    context.policy = context.skill


@then("ela aplica os defaults quando a pessoa não informa direção visual")
def then_defaults_apply_without_direction(context) -> None:
    assert "não informa direção visual" in context.policy
    assert "defaults" in context.policy


@then("ela registra exceções com alcance definido")
def then_exceptions_have_scope(context) -> None:
    assert "alcance" in context.policy
    assert "exceções" in context.policy


@then("ela preserva a personalidade do produto na hierarquia de informação")
def then_product_personality_is_preserved(context) -> None:
    assert "personalidade" in context.policy
    assert "hierarquia" in context.policy


@given("o instalador e o catálogo de especialistas do Specsfy")
def given_design_system_integration(context) -> None:
    context.installer = (ROOT / "cli" / "src" / "installer.ts").read_text(
        encoding="utf-8"
    )
    context.catalog = json.loads(
        (ROOT / "specialists" / "catalog.json").read_text(encoding="utf-8")
    )
    context.interface = (ROOT / "skills" / "templates" / "Interface.md").read_text(
        encoding="utf-8"
    )


@when("a integração do design system é lida")
def when_design_system_integration_is_read(context) -> None:
    context.integration = (
        context.installer,
        context.catalog,
        context.interface,
    )


@then("o CLI publica o template DESIGNSYSTEM.MD")
def then_cli_publishes_design_system(context) -> None:
    assert '"DESIGNSYSTEM.MD"' in context.integration[0]


@then("o especialista de experiência depende do especialista de design system")
def then_interface_experience_requires_design_system(context) -> None:
    entries = context.integration[1]["skills"]
    entry = next(
        item
        for item in entries
        if item["name"] == "specsfy-specialist-interface-experience"
    )
    assert "specsfy-specialist-design-system" in entry["requires"]


@then("o template Interface.md aponta para DESIGNSYSTEM.MD")
def then_interface_template_points_to_design_system(context) -> None:
    assert "DESIGNSYSTEM.MD" in context.integration[2]


@given("o contrato de setup do Specsfy")
def given_setup_contract(context) -> None:
    context.setup_contract = (
        ROOT / "skills" / "specsfy-setup" / "SKILL.md"
    ).read_text(encoding="utf-8")


@when("a cobertura funcional do setup é lida")
def when_setup_functional_coverage_is_read(context) -> None:
    context.setup_coverage = " ".join(context.setup_contract.split())


@then("cada entidade de negócio tem a necessidade de CRUD verificada")
def then_setup_checks_crud_need(context) -> None:
    assert "criar, consultar, editar e apagar" in context.setup_coverage


@then("cada tela aplicável tem um caminho pelos menus do sistema")
def then_setup_maps_system_menus(context) -> None:
    assert "menus do sistema" in context.setup_coverage
    assert "item, o destino, a permissão" in context.setup_coverage


@then("dúvidas sobre CRUD ou menus são confirmadas com a pessoa")
def then_setup_confirms_unclear_crud_or_menus(context) -> None:
    assert "confirme com a pessoa" in context.setup_coverage


@then("a documentação técnica completa é reconstruída durante o setup")
def then_setup_rebuilds_complete_documentation(context) -> None:
    assert "todo o sistema existente" in context.setup_coverage
    assert "$specsfy-documentator" in context.setup_coverage
