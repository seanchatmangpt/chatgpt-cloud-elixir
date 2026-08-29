defmodule ChatGPTCloud.ProcessIntelligence do
  @moduledoc "Ash-native control and projection domain for process-intelligence evidence."

  use Ash.Domain,
    extensions: [AshAdmin.Domain, AshJsonApi.Domain, AshGraphql.Domain, AshAi, AshPaperTrail.Domain]

  admin do
    show?(true)
  end

  json_api do
    routes do
      base_route "/qualifications", ChatGPTCloud.ProcessIntelligence.Qualification do
        get :read
        index :read
      end

      base_route "/cost-observations", ChatGPTCloud.ProcessIntelligence.CostObservation do
        get :read
        index :read
      end
    end
  end

  graphql do
    queries do
      get ChatGPTCloud.ProcessIntelligence.Qualification, :qualification, :read
      list ChatGPTCloud.ProcessIntelligence.Qualification, :qualifications, :read
      get ChatGPTCloud.ProcessIntelligence.CostObservation, :cost_observation, :read
      list ChatGPTCloud.ProcessIntelligence.CostObservation, :cost_observations, :read
    end
  end

  tools do
    tool(:list_qualifications, ChatGPTCloud.ProcessIntelligence.Qualification, :read,
      description:
        "Read qualification evidence and bounded standing. This tool cannot actuate deployments."
    )

    tool(:list_cost_observations, ChatGPTCloud.ProcessIntelligence.CostObservation, :read,
      description: "Read metering observations. Values are evidence, not billing authority."
    )

    tool(:list_conformance_results, ChatGPTCloud.ProcessIntelligence.ConformanceResult, :read,
      description:
        "Read process-conformance fitness evidence against declared process models. This tool cannot actuate deployments."
    )

    tool(:list_refusals, ChatGPTCloud.ProcessIntelligence.Refusal, :read,
      description:
        "Read typed REFUSED_* evidence recorded against runs. This tool cannot actuate deployments."
    )

    tool(:list_process_variants, ChatGPTCloud.ProcessIntelligence.ProcessVariant, :read,
      description:
        "Read discovered/declared process-model variants. This tool cannot actuate deployments."
    )

    tool(:list_swarm_teams, ChatGPTCloud.ProcessIntelligence.SwarmTeam, :read,
      description:
        "Read swarm coordination teams and their completed-work-item velocity aggregate. This tool cannot actuate deployments."
    )
  end

  resources do
    resource ChatGPTCloud.ProcessIntelligence.Agent
    resource ChatGPTCloud.ProcessIntelligence.Run
    resource ChatGPTCloud.ProcessIntelligence.Event
    resource ChatGPTCloud.ProcessIntelligence.Object
    resource ChatGPTCloud.ProcessIntelligence.EventObject
    resource ChatGPTCloud.ProcessIntelligence.ObjectObject
    resource ChatGPTCloud.ProcessIntelligence.Receipt
    resource ChatGPTCloud.ProcessIntelligence.ConformanceResult
    resource ChatGPTCloud.ProcessIntelligence.Refusal
    resource ChatGPTCloud.ProcessIntelligence.ProcessVariant
    resource ChatGPTCloud.ProcessIntelligence.Qualification
    resource ChatGPTCloud.ProcessIntelligence.CostObservation
    # AshPaperTrail auto-generates this Version resource but does not
    # auto-register it in the domain's resources list -- without this line,
    # `mix ash.codegen`/`mix ash_postgres.generate_migrations` silently skip
    # it (confirmed live: it reported "no changes detected" before this fix).
    resource ChatGPTCloud.ProcessIntelligence.CostObservation.Version
    resource ChatGPTCloud.ProcessIntelligence.SecretCredential
    resource ChatGPTCloud.ProcessIntelligence.SwarmAgent
    resource ChatGPTCloud.ProcessIntelligence.SwarmWorkItem
    resource ChatGPTCloud.ProcessIntelligence.SwarmTeam
  end
end
