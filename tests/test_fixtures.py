"""Testes para validar as fixtures do módulo tests/fixtures."""


from tests.fixtures import (
    create_mock_bot,
    create_mock_chat_completion,
    create_mock_embedding,
    create_mock_guild,
    create_mock_interaction,
    create_mock_message,
    create_mock_openai_client,
    create_mock_user,
    create_test_graph_edge,
    create_test_graph_node,
    create_test_memory_item,
    create_test_user,
    get_faker,
)


class TestDiscordMocks:
    """Testes para mocks do Discord."""

    def test_create_mock_user(self):
        """Testa criação de mock de usuario Discord."""
        user = create_mock_user(
            user_id="123456",
            username="TestUser",
            bot=False,
        )

        assert user.id == "123456"
        assert user.username == "TestUser"
        assert user.bot is False
        assert user.mention == "<@123456>"

    def test_create_mock_message(self):
        """Testa criacao de mock de mensagem Discord."""
        message = create_mock_message(
            content="Hello, world!",
            author=create_mock_user(user_id="123456"),
        )

        assert message.content == "Hello, world!"
        assert message.author.id == "123456"
        assert message.add_reaction is not None
        assert message.reply is not None

    def test_create_mock_interaction(self):
        """Testa criacao de mock de interacao Discord."""
        interaction = create_mock_interaction(
            response_done=True,
        )

        assert interaction.response.is_done()
        assert interaction.response.send_message is not None
        assert interaction.followup.send is not None

    def test_create_mock_guild(self):
        """Testa criacao de mock de servidor Discord."""
        guild = create_mock_guild(
            guild_id="999888777",
            name="Test Server",
        )

        assert guild.id == "999888777"
        assert guild.name == "Test Server"
        assert guild.member_count == 100

    def test_create_mock_bot(self):
        """Testa criacao de mock de bot Discord."""
        bot = create_mock_bot(
            latency=0.05,
            guilds_count=3,
        )

        assert bot.user is not None
        assert bot.user.bot is True
        assert bot.latency == 0.05
        assert len(bot.guilds) == 3
        assert bot.tree.sync is not None


class TestOpenAIMocks:
    """Testes para mocks do OpenAI."""

    def test_create_mock_embedding(self):
        """Testa criacao de mock de resposta de embedding."""
        embedding = create_mock_embedding(embedding_dim=768)

        assert "data" in embedding
        assert len(embedding["data"]) == 1
        assert len(embedding["data"][0]["embedding"]) == 768
        assert embedding["model"] == "text-embedding-3-small"

    def test_create_mock_chat_completion(self):
        """Testa criacao de mock de resposta de chat."""
        chat = create_mock_chat_completion(
            content="Test response",
        )

        assert "choices" in chat
        assert len(chat["choices"]) == 1
        assert chat["choices"][0]["message"]["content"] == "Test response"

    def test_create_mock_openai_client(self):
        """Testa criacao de mock de cliente OpenAI."""
        client = create_mock_openai_client()

        assert client.embeddings is not None
        assert client.embeddings.create is not None
        assert client.chat is not None
        assert client.chat.completions is not None
        assert client.chat.completions.create is not None


class TestFactories:
    """Testes para factories de dados de teste."""

    def test_get_faker(self):
        """Testa obtencao da instancia do Faker."""
        fake = get_faker()

        assert fake is not None
        assert hasattr(fake, "name")
        assert hasattr(fake, "email")
        assert hasattr(fake, "sentence")

    def test_create_test_user(self):
        """Testa criacao de dados de usuario de teste."""
        user = create_test_user(
            username="testuser",
            is_bot=True,
        )

        assert user["username"] == "testuser"
        assert user["is_bot"] is True
        assert "id" in user
        assert "email" in user

    def test_create_test_memory_item_core(self):
        """Testa criacao de item de memoria core."""
        item = create_test_memory_item(
            tier="core",
            importance=0.8,
        )

        assert item["importance"] == 0.8
        assert "access_count" in item
        assert "last_accessed" in item

    def test_create_test_memory_item_recall(self):
        """Testa criacao de item de memoria recall."""
        item = create_test_memory_item(tier="recall")

        assert "conversation_id" in item
        assert "relevance_score" in item
        assert item["embedding"] is None

    def test_create_test_memory_item_archival(self):
        """Testa criacao de item de memoria archival."""
        item = create_test_memory_item(tier="archival")

        assert item["tier"] == "archival"
        assert "compressed" in item
        assert "storage_location" in item
        assert "tags" in item

    def test_create_test_graph_node(self):
        """Testa criacao de no de grafo."""
        node = create_test_graph_node(
            label="Python",
            node_type="language",
        )

        assert node["label"] == "Python"
        assert node["node_type"] == "language"
        assert "embedding" in node
        assert len(node["embedding"]) == 1536

    def test_create_test_graph_edge(self):
        """Testa criacao de aresta de grafo."""
        edge = create_test_graph_edge(
            edge_type="relates_to",
            weight=1.5,
        )

        assert edge["edge_type"] == "relates_to"
        assert edge["weight"] == 1.5
        assert "source_id" in edge
        assert "target_id" in edge
