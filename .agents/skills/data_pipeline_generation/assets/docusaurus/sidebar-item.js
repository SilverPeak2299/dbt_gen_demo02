// Add this category to the consuming repository's Docusaurus sidebar.
{
  type: 'category',
  label: '{{pipeline_context_title}}',
  link: {
    type: 'doc',
    id: '{{pipeline_context_slug}}/overview',
  },
  items: [
    '{{pipeline_context_slug}}/overview',
    '{{pipeline_context_slug}}/dbt-pipeline',
    '{{pipeline_context_slug}}/data-definition',
    '{{pipeline_context_slug}}/mappings',
    '{{pipeline_context_slug}}/design',
    '{{pipeline_context_slug}}/diagrams',
    '{{pipeline_context_slug}}/assumptions',
  ],
}
